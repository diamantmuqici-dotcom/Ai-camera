package com.diamantmuqici.claritycam

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import androidx.camera.core.ImageProxy
import java.io.ByteArrayOutputStream
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToInt

/** CPU processing runs on analysis / capture workers, never the camera preview/UI thread. */
object DetailEngine {
    private fun color(value: Float) = value.roundToInt().coerceIn(0, 255)
    private fun luminance(pixel: Int): Int = (((pixel shr 16 and 255) * 54 +
        (pixel shr 8 and 255) * 183 + (pixel and 255) * 19) shr 8)

    fun averageLight(image: ImageProxy): Float {
        val plane = image.planes[0]
        var total = 0L
        var count = 0
        for (y in 0 until image.height step 24) {
            for (x in 0 until image.width step 24) {
                val index = y * plane.rowStride + x * plane.pixelStride
                if (index < plane.buffer.limit()) {
                    total += (plane.buffer.get(index).toInt() and 255)
                    count++
                }
            }
        }
        return if (count > 0) total.toFloat() / count else 0f
    }

    fun focusScore(image: ImageProxy): Float {
        val plane = image.planes[0]
        val bytes = plane.buffer
        val step = 6
        var total = 0L
        var samples = 0
        for (y in step until image.height - step step step) {
            for (x in step until image.width - step step step) {
                val index = y * plane.rowStride + x * plane.pixelStride
                val right = index + step * plane.pixelStride
                val below = index + step * plane.rowStride
                if (below >= bytes.limit() || right >= bytes.limit()) continue
                val value = bytes.get(index).toInt() and 255
                total += abs(value - (bytes.get(right).toInt() and 255))
                total += abs(value - (bytes.get(below).toInt() and 255))
                samples += 2
            }
        }
        return if (samples > 0) total.toFloat() / samples else 0f
    }

    /** Convert the latest YUV frame directly to a bounded RGB bitmap for on-device OCR. */
    fun analysisBitmap(image: ImageProxy): Bitmap {
        require(image.planes.size >= 3) { "Camera analysis did not provide YUV planes" }
        val scale = min(1f, 1600f / max(image.width, image.height))
        val width = max(1, (image.width * scale).roundToInt())
        val height = max(1, (image.height * scale).roundToInt())
        val y = image.planes[0]
        val u = image.planes[1]
        val v = image.planes[2]
        val out = IntArray(width * height)
        for (row in 0 until height) {
            val sourceY = min(image.height - 1, (row / scale).toInt())
            for (col in 0 until width) {
                val sourceX = min(image.width - 1, (col / scale).toInt())
                val yi = sourceY * y.rowStride + sourceX * y.pixelStride
                val ui = sourceY / 2 * u.rowStride + sourceX / 2 * u.pixelStride
                val vi = sourceY / 2 * v.rowStride + sourceX / 2 * v.pixelStride
                val light = (y.buffer.get(yi).toInt() and 255) - 16
                val blueDiff = (u.buffer.get(ui).toInt() and 255) - 128
                val redDiff = (v.buffer.get(vi).toInt() and 255) - 128
                val c = max(0, light)
                val red = ((298 * c + 409 * redDiff + 128) shr 8).coerceIn(0, 255)
                val green = ((298 * c - 100 * blueDiff - 208 * redDiff + 128) shr 8).coerceIn(0, 255)
                val blue = ((298 * c + 516 * blueDiff + 128) shr 8).coerceIn(0, 255)
                out[row * width + col] = -0x1000000 or (red shl 16) or (green shl 8) or blue
            }
        }
        val bitmap = Bitmap.createBitmap(out, width, height, Bitmap.Config.ARGB_8888)
        val rotation = image.imageInfo.rotationDegrees
        if (rotation == 0) return bitmap
        val rotated = Bitmap.createBitmap(bitmap, 0, 0, width, height,
            Matrix().apply { postRotate(rotation.toFloat()) }, true)
        bitmap.recycle()
        return rotated
    }

    /** Correct tone and chroma, then apply a bounded spatial filter in-place. */
    fun enhance(bitmap: Bitmap, settings: Tuning): Bitmap {
        val width = bitmap.width
        val height = bitmap.height
        val pixels = IntArray(width * height)
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height)
        val lut = IntArray(256) { index ->
            var value = (index / 255f).toDouble().pow((1f / settings.gamma).toDouble()).toFloat()
            value += settings.shadows * (1f - value) * (1f - value) * .26f
            value -= settings.highlights * max(0f, value - .55f) * (1f - value)
            color(((value - .5f) * settings.contrast + .5f) * 255f)
        }
        for (i in pixels.indices) {
            val original = pixels[i]
            val light = luminance(original)
            val balanced = lut[light]
            val r = color(balanced + ((original shr 16 and 255) - light) * settings.saturation)
            val g = color(balanced + ((original shr 8 and 255) - light) * settings.saturation)
            val b = color(balanced + ((original and 255) - light) * settings.saturation)
            pixels[i] = -0x1000000 or (r shl 16) or (g shl 8) or b
        }
        if (width > 2 && height > 2 && (settings.clarity > 0f || settings.denoise > 0)) {
            // Only three row buffers: do not allocate another full-size capture image.
            var previous = pixels.copyOfRange(0, width)
            var current = pixels.copyOfRange(width, width * 2)
            var next = pixels.copyOfRange(width * 2, width * 3)
            for (row in 1 until height - 1) {
                for (col in 1 until width - 1) {
                    val center = luminance(current[col])
                    val blur = (center * 4 + luminance(current[col - 1]) +
                        luminance(current[col + 1]) + luminance(previous[col]) +
                        luminance(next[col])) / 8f
                    val noiseCorrection = if (settings.denoise > 0 &&
                        abs(center - blur) < settings.denoise * 9f) (blur - center) * .55f else 0f
                    val delta = noiseCorrection + (center - blur) * settings.clarity * .6f
                    val source = current[col]
                    pixels[row * width + col] = -0x1000000 or
                        (color((source shr 16 and 255) + delta) shl 16) or
                        (color((source shr 8 and 255) + delta) shl 8) or
                        color((source and 255) + delta)
                }
                previous = current
                current = next
                if (row + 2 < height) next = pixels.copyOfRange((row + 2) * width, (row + 3) * width)
            }
        }
        val result = Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888)
        return result
    }

    /** Enhanced JPEG is bounded at about 12 MP to keep memory safe; original stays full-size. */
    fun enhancedJpeg(originalJpeg: ByteArray, degrees: Int, mirror: Boolean, settings: Tuning): ByteArray {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(originalJpeg, 0, originalJpeg.size, bounds)
        require(bounds.outWidth > 0 && bounds.outHeight > 0) { "Camera returned an unreadable JPEG" }
        var sample = 1
        while (bounds.outWidth / sample * (bounds.outHeight / sample) > 12_000_000) sample *= 2
        val decoded = BitmapFactory.decodeByteArray(originalJpeg, 0, originalJpeg.size,
            BitmapFactory.Options().apply { inSampleSize = sample })
            ?: error("Could not decode camera capture")
        val matrix = Matrix().apply {
            postRotate(degrees.toFloat())
            if (mirror) postScale(-1f, 1f)
        }
        val upright = if (degrees != 0 || mirror) Bitmap.createBitmap(decoded, 0, 0,
            decoded.width, decoded.height, matrix, true) else decoded
        if (upright !== decoded) decoded.recycle()
        val enhanced = enhance(upright, settings)
        upright.recycle()
        return ByteArrayOutputStream().use { output ->
            try {
                check(enhanced.compress(Bitmap.CompressFormat.JPEG, 94, output)) { "JPEG encoder failed" }
                output.toByteArray()
            } finally { enhanced.recycle() }
        }
    }
}
