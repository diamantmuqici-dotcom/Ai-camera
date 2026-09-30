package com.diamantmuqici.claritycam

import android.graphics.ImageFormat
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.TotalCaptureResult
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Range
import androidx.annotation.OptIn
import androidx.camera.camera2.interop.Camera2CameraInfo
import androidx.camera.camera2.interop.Camera2Interop
import androidx.camera.camera2.interop.ExperimentalCamera2Interop
import androidx.camera.core.AspectRatio
import androidx.camera.core.Camera
import androidx.camera.core.CameraFilter
import androidx.camera.core.CameraInfo
import androidx.camera.core.CameraSelector
import androidx.camera.core.FocusMeteringAction
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.ZoomState
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Observer
import com.google.mlkit.vision.text.TextRecognizer
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.math.abs

/** CameraX preview/capture + Camera2 controls. 0.5× only if a physical wide view is exposed. */
@OptIn(ExperimentalCamera2Interop::class)
class CameraController(
    private val activity: MainActivity,
    private val view: PreviewView,
    private val recognizer: TextRecognizer,
    private val tuning: () -> Tuning,
    private val listener: Listener,
) {
    interface Listener {
        fun onState(message: String)
        fun onProblem(title: String, message: String)
        fun onStreaming()
        fun onFps(value: Int)
        fun onZoom(value: Float, max: Float, halfAvailable: Boolean, torchAvailable: Boolean)
        fun onTargets(targets: List<ScanTarget>, focus: Float, light: Float, width: Int, height: Int, front: Boolean)
        fun onHint(message: String)
        fun onSaved(uri: Uri)
        fun onCaptureError(message: String)
    }

    private val main = ContextCompat.getMainExecutor(activity)
    private val cameraManager = activity.getSystemService(CameraManager::class.java)
    private val analysisExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private val captureExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private var provider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var capture: ImageCapture? = null
    private var zoomObserver: Observer<ZoomState>? = null
    private var mainId: String? = null
    private var ultrawide: WideLens? = null
    private var logicalHalf = false
    private var front = false
    private var usingWide = false
    private var wantedZoom = 1f
    private var generation = 0
    private var torchOn = false
    private var disposed = false

    private data class WideLens(val id: String, val factor: Float)
    val isFront get() = front
    val currentZoom get() = wantedZoom

    init {
        view.previewStreamState.observe(activity) { state ->
            if (state == PreviewView.StreamState.STREAMING) listener.onStreaming()
        }
    }

    fun start() {
        if (disposed) return
        listener.onState("OPENING CAMERA")
        val pending = ProcessCameraProvider.getInstance(activity)
        pending.addListener({
            if (disposed) return@addListener
            try {
                provider = pending.get()
                discoverLenses()
                bind()
            } catch (error: Exception) {
                listener.onProblem("Camera unavailable", error.localizedMessage ?: "No accessible camera. Check device permissions.")
            }
        }, main)
    }

    private fun cameraId(info: CameraInfo) = Camera2CameraInfo.from(info).cameraId

    private fun focalLength(id: String): Float? = try {
        cameraManager.getCameraCharacteristics(id)
            .get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)
            ?.filter { it > 0f }?.sorted()?.let { it[it.size / 2] }
    } catch (_: Exception) { null }

    private fun discoverLenses() {
        val infos = provider?.availableCameraInfos.orEmpty()
            .filter { it.lensFacing == CameraSelector.LENS_FACING_BACK }
        val primary = CameraSelector.DEFAULT_BACK_CAMERA.filter(infos).firstOrNull()
            ?: error("No rear camera is exposed to this app")
        mainId = cameraId(primary)
        val reference = focalLength(mainId!!) ?: return
        ultrawide = infos.mapNotNull { info ->
            val id = cameraId(info)
            if (id == mainId) return@mapNotNull null
            val focal = focalLength(id) ?: return@mapNotNull null
            val factor = focal / reference
            if (factor in .35f.. .57f) WideLens(id, factor) else null
        }.minByOrNull { it.factor }
        logicalHalf = (primary.zoomState.value?.minZoomRatio ?: 1f) <= .55f
    }

    private fun selectFps(id: String?, fps: Int): Range<Int>? {
        if (id == null || fps == 0) return null
        return try {
            val ranges = cameraManager.getCameraCharacteristics(id)
                .get(CameraCharacteristics.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES).orEmpty()
            ranges.filter { it.lower <= fps && it.upper >= fps }
                .maxByOrNull { it.lower }
        } catch (_: Exception) { null }
    }

    private fun selectedCamera(): CameraSelector {
        if (front) return CameraSelector.DEFAULT_FRONT_CAMERA
        val wide = ultrawide
        if (!usingWide || wide == null) return CameraSelector.DEFAULT_BACK_CAMERA
        return CameraSelector.Builder().requireLensFacing(CameraSelector.LENS_FACING_BACK)
            .addCameraFilter(CameraFilter { infos -> infos.filter { cameraId(it) == wide.id } })
            .build()
    }

    fun bind(fpsOverride: Int? = null) {
        val source = provider ?: return
        generation++
        val localGeneration = generation
        camera?.cameraInfo?.zoomState?.let { live -> zoomObserver?.let { live.removeObserver(it) } }
        zoomObserver = null
        source.unbindAll()
        camera = null
        capture = null
        torchOn = false
        listener.onState("CONNECTING TO SENSOR")
        try {
            val selector = selectedCamera()
            val id = selector.filter(source.availableCameraInfos).firstOrNull()?.let { cameraId(it) }
            val previewBuilder = Preview.Builder().setTargetAspectRatio(AspectRatio.RATIO_16_9)
            val interop = Camera2Interop.Extender(previewBuilder)
            val fps = fpsOverride ?: tuning().fps
            val chosen = selectFps(id, fps)
            if (fps != 0 && chosen == null) listener.onHint("${fps} FPS is not available on this lens; using camera auto.")
            if (chosen != null) interop.setCaptureRequestOption(CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE, chosen)
            val samples = ArrayDeque<Long>()
            var lastUpdate = 0L
            interop.setSessionCaptureCallback(object : CameraCaptureSession.CaptureCallback() {
                override fun onCaptureCompleted(session: CameraCaptureSession, request: CaptureRequest,
                                                result: TotalCaptureResult) {
                    val now = SystemClock.elapsedRealtime()
                    synchronized(samples) {
                        samples.addLast(now)
                        while (samples.isNotEmpty() && now - samples.first() > 1000L) samples.removeFirst()
                        if (now - lastUpdate >= 1000L) {
                            lastUpdate = now
                            val count = samples.size
                            handler.post { if (generation == localGeneration) listener.onFps(count) }
                        }
                    }
                }
            })
            val preview = previewBuilder.build()
            val analysis = ImageAnalysis.Builder()
                .setTargetAspectRatio(AspectRatio.RATIO_16_9)
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
            analysis.setAnalyzer(analysisExecutor, OnDeviceAnalyzer(recognizer, main, tuning,
                { targets, focus, light, width, height ->
                    if (generation == localGeneration) listener.onTargets(targets, focus, light, width, height, front)
                }, { message -> if (generation == localGeneration) listener.onHint(message) }))
            val photo = ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                .setTargetAspectRatio(AspectRatio.RATIO_16_9)
                .build()
            preview.surfaceProvider = view.surfaceProvider
            val bound = source.bindToLifecycle(activity, selector, preview, analysis, photo)
            camera = bound
            capture = photo
            val requestedZoom = wantedZoom // LiveData may notify synchronously when observed.
            val info = bound.cameraInfo
            val observer = Observer<ZoomState> { state ->
                if (generation == localGeneration && state != null) {
                    if (!front && !usingWide) logicalHalf = state.minZoomRatio <= .55f
                    val base = if (usingWide) ultrawide?.factor ?: .5f else 1f
                    val current = state.zoomRatio * base
                    wantedZoom = current
                    listener.onZoom(current, state.maxZoomRatio * base,
                        !front && (logicalHalf || ultrawide != null), info.hasFlashUnit())
                }
            }
            zoomObserver = observer
            info.zoomState.observe(activity, observer)
            val ratio = if (usingWide) 1f else requestedZoom
            val limits = info.zoomState.value
            bound.cameraControl.setZoomRatio(ratio.coerceIn(
                limits?.minZoomRatio ?: 1f, limits?.maxZoomRatio ?: 1f))
            setExposure(tuning().exposureIndex)
            listener.onState("SCANNING LOCALLY")
        } catch (error: Exception) {
            if (fpsOverride == null && tuning().fps != 0) {
                listener.onHint("Requested frame rate could not start; retrying in camera auto mode.")
                bind(fpsOverride = 0)
            } else {
                listener.onProblem("Camera could not start", error.localizedMessage ?: "Try another lens or check permissions.")
            }
        }
    }

    fun zoomTo(value: Float) {
        if (provider == null || camera == null) return
        if (value < .85f && !front) {
            if (!logicalHalf && ultrawide == null) { listener.onHint("0.5× needs an exposed physical ultrawide camera."); return }
            if (logicalHalf) {
                if (usingWide) { usingWide = false; wantedZoom = .5f; bind() }
                else {
                    wantedZoom = .5f
                    camera?.cameraControl?.setZoomRatio(.5f)
                }
            } else {
                if (!usingWide) { usingWide = true; wantedZoom = ultrawide!!.factor; bind() }
            }
            return
        }
        if (usingWide) {
            usingWide = false
            wantedZoom = value.coerceAtLeast(1f)
            bind()
            return
        }
        val bounds = camera?.cameraInfo?.zoomState?.value ?: return
        wantedZoom = value.coerceIn(bounds.minZoomRatio.coerceAtLeast(1f), bounds.maxZoomRatio)
        camera?.cameraControl?.setZoomRatio(wantedZoom)
    }

    fun flip() {
        front = !front
        usingWide = false
        wantedZoom = 1f
        bind()
    }

    fun toggleTorch() {
        val bound = camera ?: return
        if (!bound.cameraInfo.hasFlashUnit()) { listener.onHint("This camera has no torch."); return }
        torchOn = !torchOn
        bound.cameraControl.enableTorch(torchOn)
        listener.onHint(if (torchOn) "Light on" else "Light off")
    }

    fun tapToFocus(x: Float, y: Float) {
        val bound = camera ?: return
        val point = view.meteringPointFactory.createPoint(x, y)
        val action = FocusMeteringAction.Builder(point,
            FocusMeteringAction.FLAG_AF or FocusMeteringAction.FLAG_AE)
            .setAutoCancelDuration(4, TimeUnit.SECONDS).build()
        bound.cameraControl.startFocusAndMetering(action)
        listener.onHint("Focusing at touch point")
    }

    fun exposureRange(): Range<Int>? = camera?.cameraInfo?.exposureState?.exposureCompensationRange
    fun setExposure(index: Int) {
        val range = exposureRange() ?: return
        if (range.lower < range.upper) camera?.cameraControl?.setExposureCompensationIndex(
            index.coerceIn(range.lower, range.upper))
    }

    fun takePicture() {
        val photo = capture ?: run { listener.onCaptureError("Camera is not ready"); return }
        photo.takePicture(captureExecutor, object : ImageCapture.OnImageCapturedCallback() {
            override fun onCaptureSuccess(image: ImageProxy) {
                var closed = false
                try {
                    require(image.format == ImageFormat.JPEG) { "Camera did not return a JPEG" }
                    val buffer = image.planes[0].buffer
                    val bytes = ByteArray(buffer.remaining())
                    buffer.get(bytes)
                    val rotation = image.imageInfo.rotationDegrees
                    image.close()
                    closed = true
                    val result = CaptureStore.save(activity, bytes, rotation, front, tuning())
                    main.execute { if (!disposed) listener.onSaved(result) }
                } catch (error: Exception) {
                    if (!closed) image.close()
                    main.execute { if (!disposed) listener.onCaptureError(error.localizedMessage ?: "Could not save photo") }
                }
            }
            override fun onError(exception: ImageCaptureException) {
                main.execute { if (!disposed) listener.onCaptureError(exception.localizedMessage ?: "Camera capture failed") }
            }
        })
    }

    fun close() {
        disposed = true
        generation++
        provider?.unbindAll()
        analysisExecutor.shutdown()
        captureExecutor.shutdown()
    }
}
