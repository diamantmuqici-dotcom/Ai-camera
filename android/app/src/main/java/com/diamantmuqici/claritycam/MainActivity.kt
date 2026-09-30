package com.diamantmuqici.claritycam

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.provider.MediaStore
import android.provider.Settings
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import com.diamantmuqici.claritycam.databinding.ActivityMainBinding
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.util.Locale
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.abs
import kotlin.math.roundToInt

/** Full-screen native Activity; explicit permission/no-camera/retry states prevent a black screen. */
class MainActivity : ComponentActivity(), CameraController.Listener {
    private lateinit var ui: ActivityMainBinding
    private val recognizer by lazy { TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS) }
    private var controller: CameraController? = null
    private lateinit var tuning: Tuning
    private val snapper = StableSnapper()
    private val captureBusy = AtomicBoolean(false)
    private val handler = Handler(Looper.getMainLooper())
    private var streaming = false
    private var permissionProblem = false
    private var lastTarget: ScanTarget? = null
    private var lastUri: Uri? = null
    private val permissionRequest = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) startCamera() else showProblem("Camera access needed",
            "Allow camera access in Android settings. Your camera and OCR stay on this device.", permission = true)
    }
    private val noPreview = Runnable {
        if (!streaming) showProblem("No live frames",
            "Camera opened but no preview arrived. Check your privacy switch, close other camera apps, then retry.")
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        ui = ActivityMainBinding.inflate(layoutInflater)
        setContentView(ui.root)
        ViewCompat.setOnApplyWindowInsetsListener(ui.root) { _, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            ui.topBar.updatePadding(top = bars.top + dp(12))
            ui.bottomPanel.updatePadding(bottom = bars.bottom + dp(12))
            (ui.hint.layoutParams as android.widget.FrameLayout.LayoutParams).also {
                it.topMargin = bars.top + dp(82)
                ui.hint.layoutParams = it
            }
            insets
        }
        tuning = Tuning.load(this)
        lastUri = getSharedPreferences("clarity_v2", MODE_PRIVATE)
            .getString("lastUri", null)?.let(Uri::parse)
        setupControls()
        updateMode()
        ui.autoSwitch.isChecked = tuning.autoSnap
        showConnecting("Waiting for camera permission…")
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
            startCamera()
        else permissionRequest.launch(Manifest.permission.CAMERA)
    }

    private fun dp(value: Int) = (resources.displayMetrics.density * value).roundToInt()
    private fun persist() { tuning.save(this) }
    private fun hint(text: String) {
        ui.hint.text = text
        ui.hint.contentDescription = text
    }

    private fun setupControls() {
        ui.retryButton.setOnClickListener {
            if (permissionProblem) {
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:$packageName")))
            } else startCamera()
        }
        ui.plateMode.setOnClickListener { setMode(ScanMode.PLATE) }
        ui.textMode.setOnClickListener { setMode(ScanMode.TEXT) }
        ui.autoSwitch.setOnCheckedChangeListener { _, active ->
            tuning = tuning.copy(autoSnap = active)
            snapper.reset()
            persist()
            hint(if (active) "Auto snap: stable text after ${tuning.autoZoom}×" else "Auto snap off • shutter is manual")
        }
        ui.scanResult.setOnClickListener {
            val text = lastTarget?.text ?: return@setOnClickListener
            (getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager)
                .setPrimaryClip(ClipData.newPlainText("Recognized candidate", text))
            Toast.makeText(this, "Text copied; please verify OCR characters", Toast.LENGTH_SHORT).show()
        }
        listOf(ui.zoom05 to .5f, ui.zoom1 to 1f, ui.zoom2 to 2f,
            ui.zoom4 to 4f, ui.zoom8 to 8f).forEach { (control, value) ->
            control.setOnClickListener { controller?.zoomTo(value) }
        }
        ui.zoomSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seek: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) controller?.zoomTo(1f + progress / 100f)
            }
            override fun onStartTrackingTouch(seek: SeekBar?) {}
            override fun onStopTrackingTouch(seek: SeekBar?) {}
        })
        ui.shutterButton.setOnClickListener { takePhoto(false) }
        ui.flipButton.setOnClickListener { controller?.flip(); snapper.reset(); ui.overlay.show(emptyList(), 16, 9, false) }
        ui.torchButton.setOnClickListener { controller?.toggleTorch() }
        ui.tuneButton.setOnClickListener { showSettings() }
        ui.settingsTop.setOnClickListener { showSettings() }
        ui.galleryButton.setOnClickListener { openGallery() }
        val pinch = ScaleGestureDetector(this, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScale(detector: ScaleGestureDetector): Boolean {
                controller?.let { it.zoomTo(it.currentZoom * detector.scaleFactor) }
                return true
            }
        })
        val tap = GestureDetector(this, object : GestureDetector.SimpleOnGestureListener() {
            override fun onDown(event: MotionEvent): Boolean = true
            override fun onSingleTapUp(event: MotionEvent): Boolean {
                controller?.tapToFocus(event.x, event.y)
                return true
            }
        })
        ui.preview.setOnTouchListener { _, event ->
            pinch.onTouchEvent(event)
            if (event.pointerCount == 1 && !pinch.isInProgress) tap.onTouchEvent(event)
            true
        }
    }

    private fun setMode(mode: ScanMode) {
        tuning = tuning.copy(scanMode = mode)
        persist()
        lastTarget = null
        snapper.reset()
        ui.overlay.show(emptyList(), 16, 9, controller?.isFront == true)
        ui.scanResult.text = if (mode == ScanMode.PLATE) "LOOKING FOR PLATE CANDIDATES" else "LOOKING FOR READABLE TEXT"
        updateMode()
    }

    private fun updateMode() {
        listOf(ui.plateMode to ScanMode.PLATE, ui.textMode to ScanMode.TEXT).forEach { (view, mode) ->
            val active = tuning.scanMode == mode
            view.setBackgroundResource(if (active) R.drawable.pill_active else R.drawable.pill_idle)
            view.setTextColor(ContextCompat.getColor(this, if (active) R.color.ink else R.color.pale))
        }
    }

    private fun startCamera() {
        permissionProblem = false
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            permissionRequest.launch(Manifest.permission.CAMERA)
            return
        }
        streaming = false
        ui.fpsBadge.text = "— FPS"
        showConnecting("Opening the camera; scan runs on-device…")
        if (controller == null) controller = CameraController(this, ui.preview, recognizer, { tuning }, this)
        controller?.start()
        handler.removeCallbacks(noPreview)
        handler.postDelayed(noPreview, 9_000)
    }

    private fun showConnecting(message: String) {
        ui.errorCard.visibility = View.VISIBLE
        ui.errorTitle.text = "Connecting camera"
        ui.errorMessage.text = message
        ui.retryButton.text = "RETRY"
        ui.cameraState.text = "STARTING SENSOR"
    }

    private fun showProblem(title: String, message: String, permission: Boolean = false) {
        permissionProblem = permission
        streaming = false
        ui.errorCard.visibility = View.VISIBLE
        ui.errorTitle.text = title
        ui.errorMessage.text = message
        ui.retryButton.text = if (permission) "OPEN APP SETTINGS" else "RETRY CAMERA"
        ui.cameraState.text = "CAMERA NEEDS ATTENTION"
        ui.fpsBadge.text = "NO FEED"
        hint("Camera unavailable • photos need a live frame")
    }

    override fun onResume() {
        super.onResume()
        if (::ui.isInitialized && permissionProblem &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
            startCamera()
    }

    override fun onState(message: String) { ui.cameraState.text = message }
    override fun onProblem(title: String, message: String) = showProblem(title, message)
    override fun onStreaming() {
        streaming = true
        handler.removeCallbacks(noPreview)
        ui.errorCard.visibility = View.GONE
        ui.cameraState.text = "LIVE  /  PRIVATE"
        hint("Scanning locally • tap preview to focus")
    }
    override fun onFps(value: Int) { ui.fpsBadge.text = "$value FPS" }

    override fun onZoom(value: Float, max: Float, halfAvailable: Boolean, torchAvailable: Boolean) {
        val availableMax = max.coerceAtLeast(1f)
        ui.zoom05.isEnabled = halfAvailable
        ui.zoom05.alpha = if (halfAvailable) 1f else .35f
        ui.zoom05.contentDescription = if (halfAvailable) "Physical ultrawide approximately 0.5 times" else
            "0.5 times unavailable because the camera does not expose an ultrawide lens"
        listOf(ui.zoom1 to 1f, ui.zoom2 to 2f, ui.zoom4 to 4f, ui.zoom8 to 8f)
            .forEach { (control, zoom) ->
                // Even when on a separate wide lens, the main lens can offer its own range.
                control.isEnabled = zoom <= availableMax + .02f || value < 1f
                control.alpha = if (control.isEnabled) 1f else .35f
            }
        listOf(ui.zoom05 to .5f, ui.zoom1 to 1f, ui.zoom2 to 2f, ui.zoom4 to 4f,
            ui.zoom8 to 8f).forEach { (control, zoom) ->
            val active = abs(value - zoom) < .13f
            control.setBackgroundResource(if (active) R.drawable.pill_active else R.drawable.pill_idle)
            control.setTextColor(ContextCompat.getColor(this, if (active) R.color.ink else R.color.pale))
        }
        ui.zoomSeek.max = ((availableMax - 1f) * 100).roundToInt().coerceAtLeast(1)
        ui.zoomSeek.progress = ((value.coerceAtLeast(1f) - 1f) * 100).roundToInt()
        ui.footerStatus.text = if (value < 1f)
            "PHYSICAL WIDE  ${String.format(Locale.US, "%.2f", value)}×   •   ON-DEVICE OCR"
            else "${String.format(Locale.US, "%.1f", value)}×   •   HIGH-RES PHOTO + ORIGINAL"
        ui.torchButton.alpha = if (torchAvailable) 1f else .35f
    }

    override fun onTargets(targets: List<ScanTarget>, focus: Float, width: Int, height: Int, front: Boolean) {
        val shown = if (tuning.scanMode == ScanMode.PLATE) targets.filter { it.kind == ScanMode.PLATE } else targets
        ui.overlay.show(shown, width, height, front)
        lastTarget = shown.firstOrNull()
        ui.scanResult.text = lastTarget?.let {
            (if (it.kind == ScanMode.PLATE) "PLATE?  " else "TEXT  ") + it.text
        } ?: if (focus < 5f) "HOLD STEADY  /  ADD MORE LIGHT" else "SEARCHING FOR CLEAR TEXT…"
        if (tuning.autoSnap && snapper.observe(lastTarget, controller?.currentZoom ?: 1f,
                tuning.autoZoom, focus, SystemClock.elapsedRealtime())) takePhoto(true)
    }
    override fun onHint(message: String) { hint(message) }

    private fun takePhoto(automatic: Boolean) {
        if (!streaming || !captureBusy.compareAndSet(false, true)) return
        ui.shutterButton.alpha = .45f
        ui.footerStatus.text = if (automatic) "STABLE TEXT  •  AUTO CAPTURING" else "SAVING PHOTO…"
        controller?.takePicture() ?: run { captureBusy.set(false); ui.shutterButton.alpha = 1f }
    }

    override fun onSaved(uri: Uri) {
        captureBusy.set(false)
        ui.shutterButton.alpha = 1f
        lastUri = uri
        getSharedPreferences("clarity_v2", MODE_PRIVATE).edit().putString("lastUri", uri.toString()).apply()
        hint("Photo saved to Pictures/ClarityCam • tap FILES to view")
        ui.footerStatus.text = "SAVED  •  ENHANCED + ORIGINAL"
    }
    override fun onCaptureError(message: String) {
        captureBusy.set(false)
        ui.shutterButton.alpha = 1f
        hint("Photo not saved: $message")
        ui.footerStatus.text = "CAPTURE FAILED  •  RETRY"
    }

    private fun openGallery() {
        val uri = lastUri ?: MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        val view = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, if (lastUri == null) "image/*" else "image/jpeg")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try { startActivity(view) }
        catch (_: Exception) {
            try { startActivity(Intent(Intent.ACTION_GET_CONTENT).apply { type = "image/*" }) }
            catch (_: Exception) { hint("Photos are in Pictures/ClarityCam") }
        }
    }

    private fun showSettings() {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(12), dp(20), dp(20))
        }
        fun info(text: String) {
            panel.addView(TextView(this).apply {
                this.text = text; textSize = 12f
                setTextColor(ContextCompat.getColor(this@MainActivity, R.color.muted))
                setPadding(0, dp(6), 0, dp(11))
            })
        }
        info("Changes to gamma, tone and detail affect OCR and both photo versions (the original is untouched). Camera EV affects the live preview. Heavy work never blocks preview.")
        fun slider(title: String, min: Float, max: Float, value: Float, steps: Int = 100,
                   unit: String = "", change: (Float) -> Unit) {
            val caption = TextView(this).apply {
                textSize = 14f; setTextColor(ContextCompat.getColor(this@MainActivity, R.color.pale))
                setPadding(0, dp(10), 0, 0)
            }
            val seek = SeekBar(this).apply {
                this.max = steps
                progress = (((value - min) / (max - min)) * steps).roundToInt().coerceIn(0, steps)
            }
            fun display(current: Float) {
                caption.text = "$title   ${String.format(Locale.US, "%.2f", current)}$unit"
            }
            display(value)
            panel.addView(caption)
            panel.addView(seek)
            seek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(bar: SeekBar?, progress: Int, fromUser: Boolean) {
                    if (!fromUser) return
                    val current = min + (max - min) * progress / steps
                    display(current); change(current); persist()
                }
                override fun onStartTrackingTouch(bar: SeekBar?) {}
                override fun onStopTrackingTouch(bar: SeekBar?) {}
            })
        }
        slider("Gamma", .6f, 1.8f, tuning.gamma, 120) { tuning = tuning.copy(gamma = it) }
        slider("Contrast", .7f, 1.5f, tuning.contrast, 80) { tuning = tuning.copy(contrast = it) }
        slider("Highlights", 0f, .8f, tuning.highlights, 80) { tuning = tuning.copy(highlights = it) }
        slider("Shadows", 0f, .6f, tuning.shadows, 60) { tuning = tuning.copy(shadows = it) }
        slider("Clarity", 0f, 1f, tuning.clarity) { tuning = tuning.copy(clarity = it) }
        slider("Noise reduction", 0f, 3f, tuning.denoise.toFloat(), 3) {
            tuning = tuning.copy(denoise = it.roundToInt())
        }
        slider("Color", .6f, 1.5f, tuning.saturation, 90) { tuning = tuning.copy(saturation = it) }
        slider("Auto snap at zoom", 1.5f, 4f, tuning.autoZoom, 25, "×") {
            tuning = tuning.copy(autoZoom = it); snapper.reset()
        }
        controller?.exposureRange()?.let { range ->
            if (range.lower < range.upper) slider("Camera exposure EV step", range.lower.toFloat(),
                range.upper.toFloat(), tuning.exposureIndex.coerceIn(range.lower, range.upper).toFloat(),
                range.upper - range.lower) {
                val index = it.roundToInt(); tuning = tuning.copy(exposureIndex = index)
                controller?.setExposure(index)
            }
        }
        info("FPS is a hardware request; the actual measured sensor rate is shown above the preview.")
        val choices = RadioGroup(this).apply { orientation = RadioGroup.HORIZONTAL }
        listOf(0 to "AUTO", 30 to "30", 60 to "60").forEach { (rate, title) ->
            val radio = RadioButton(this).apply {
                id = View.generateViewId()
                text = title
                textSize = 12f
                isChecked = tuning.fps == rate
                setOnClickListener {
                    if (tuning.fps != rate) {
                        tuning = tuning.copy(fps = rate); persist(); streaming = false
                        showConnecting("Reconfiguring sensor frame rate…")
                        controller?.bind()
                        handler.removeCallbacks(noPreview); handler.postDelayed(noPreview, 9_000)
                    }
                }
            }
            choices.addView(radio)
        }
        panel.addView(choices)
        info("Only actual exposed ultrawide cameras enable 0.5×. This app never pretends a digital crop widens your view. Plate boxes are OCR candidates: verify all characters manually.")
        val scroll = ScrollView(this).apply { addView(panel) }
        MaterialAlertDialogBuilder(this).setTitle("IMAGE LAB  /  V2")
            .setView(scroll).setNeutralButton("RESET", null).setPositiveButton("DONE", null)
            .create().also { dialog ->
                dialog.setOnShowListener {
                    dialog.getButton(android.app.AlertDialog.BUTTON_NEUTRAL).setOnClickListener {
                        tuning = Tuning(scanMode = tuning.scanMode, autoSnap = tuning.autoSnap)
                        persist()
                        controller?.setExposure(0)
                        dialog.dismiss(); showSettings()
                        hint("Image settings reset")
                    }
                }
                dialog.show()
            }
    }

    override fun onDestroy() {
        handler.removeCallbacks(noPreview)
        controller?.close()
        if (this::ui.isInitialized) recognizer.close()
        super.onDestroy()
    }
}
