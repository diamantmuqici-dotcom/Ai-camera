package com.diamantmuqici.claritycam

import android.os.SystemClock
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognizer
import java.util.concurrent.Executor
import java.util.concurrent.atomic.AtomicBoolean

/** Latest-frame-only OCR. CameraX preview/capture do not wait for ML Kit results. */
class OnDeviceAnalyzer(
    private val recognizer: TextRecognizer,
    private val mainExecutor: Executor,
    private val tuning: () -> Tuning,
    private val onTargets: (List<ScanTarget>, Float, Int, Int) -> Unit,
    private val onError: (String) -> Unit,
) : ImageAnalysis.Analyzer {
    private val busy = AtomicBoolean(false)
    private var lastScan = 0L

    override fun analyze(image: ImageProxy) {
        val now = SystemClock.elapsedRealtime()
        if (!busy.compareAndSet(false, true)) { image.close(); return }
        if (now - lastScan < 450L) { busy.set(false); image.close(); return }
        lastScan = now
        var closed = false
        try {
            val focus = DetailEngine.focusScore(image)
            val original = DetailEngine.analysisBitmap(image)
            image.close()
            closed = true
            val enhanced = try { DetailEngine.enhance(original, tuning()) }
                finally { original.recycle() }
            val mode = tuning().scanMode
            recognizer.process(InputImage.fromBitmap(enhanced, 0))
                .addOnSuccessListener(mainExecutor) { result ->
                    val targets = result.textBlocks.flatMap { it.lines }.mapNotNull { line ->
                        val rect = line.boundingBox ?: return@mapNotNull null
                        if (rect.width() < 5 || rect.height() < 5) return@mapNotNull null
                        val aspect = rect.width().toFloat() / rect.height()
                        val kind = if (PlateRules.isCandidate(line.text, aspect)) ScanMode.PLATE else ScanMode.TEXT
                        if (mode == ScanMode.PLATE && kind != ScanMode.PLATE) return@mapNotNull null
                        if (line.text.trim().length < 2) return@mapNotNull null
                        ScanTarget(line.text.trim(), ScanBox(
                            (rect.left.toFloat() / enhanced.width).coerceIn(0f, 1f),
                            (rect.top.toFloat() / enhanced.height).coerceIn(0f, 1f),
                            (rect.right.toFloat() / enhanced.width).coerceIn(0f, 1f),
                            (rect.bottom.toFloat() / enhanced.height).coerceIn(0f, 1f),
                        ), kind)
                    }.sortedByDescending { (it.bounds.right - it.bounds.left) *
                        (it.bounds.bottom - it.bounds.top) }.take(8)
                    onTargets(targets, focus, enhanced.width, enhanced.height)
                }
                .addOnFailureListener(mainExecutor) { onError("Text scanner unavailable: ${it.localizedMessage}") }
                .addOnCompleteListener(mainExecutor) { enhanced.recycle(); busy.set(false) }
        } catch (error: Exception) {
            if (!closed) image.close()
            busy.set(false)
            mainExecutor.execute { onError("Camera frame could not be analyzed: ${error.localizedMessage}") }
        }
    }
}
