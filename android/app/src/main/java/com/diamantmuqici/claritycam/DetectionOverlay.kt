package com.diamantmuqici.claritycam

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.util.AttributeSet
import android.view.View
import kotlin.math.max

/** Transparent, approximate FILL_CENTER mapping from OCR frames to the preview. */
class DetectionOverlay(context: Context, attrs: AttributeSet? = null) : View(context, attrs) {
    private var targets: List<ScanTarget> = emptyList()
    private var frameWidth = 16
    private var frameHeight = 9
    private var mirrored = false
    private val density = resources.displayMetrics.density
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    init { setWillNotDraw(false); isClickable = false }

    fun show(items: List<ScanTarget>, width: Int, height: Int, frontCamera: Boolean) {
        targets = items
        frameWidth = max(1, width)
        frameHeight = max(1, height)
        mirrored = frontCamera
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val mint = Color.rgb(184, 247, 200)
        val blue = Color.rgb(144, 202, 255)
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = density
        paint.color = Color.argb(34, 184, 247, 200)
        for (step in 1..2) {
            val x = width * step / 3f
            val y = height * step / 3f
            canvas.drawLine(x, 0f, x, height.toFloat(), paint)
            canvas.drawLine(0f, y, width.toFloat(), y, paint)
        }
        val cx = width / 2f
        val cy = height * .43f
        paint.color = Color.argb(150, 184, 247, 200)
        paint.strokeWidth = density * 1.5f
        canvas.drawLine(cx - 19 * density, cy, cx - 7 * density, cy, paint)
        canvas.drawLine(cx + 7 * density, cy, cx + 19 * density, cy, paint)
        canvas.drawLine(cx, cy - 19 * density, cx, cy - 7 * density, paint)
        canvas.drawLine(cx, cy + 7 * density, cx, cy + 19 * density, paint)

        val scale = max(width.toFloat() / frameWidth, height.toFloat() / frameHeight)
        val left = (width - frameWidth * scale) / 2f
        val top = (height - frameHeight * scale) / 2f
        for (target in targets) {
            val box = target.bounds
            val x1 = if (mirrored) 1f - box.right else box.left
            val x2 = if (mirrored) 1f - box.left else box.right
            val rect = RectF(left + x1 * frameWidth * scale, top + box.top * frameHeight * scale,
                left + x2 * frameWidth * scale, top + box.bottom * frameHeight * scale)
            val color = if (target.kind == ScanMode.PLATE) mint else blue
            paint.style = Paint.Style.FILL
            paint.color = Color.argb(29, Color.red(color), Color.green(color), Color.blue(color))
            canvas.drawRoundRect(rect, 8 * density, 8 * density, paint)
            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 2.5f * density
            paint.color = color
            canvas.drawRoundRect(rect, 8 * density, 8 * density, paint)
            val label = (if (target.kind == ScanMode.PLATE) "PLATE?  " else "TEXT  ") + target.text.take(20)
            paint.typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
            paint.textSize = 11 * resources.displayMetrics.scaledDensity
            val tag = RectF(rect.left.coerceAtLeast(3f), (rect.top - 26 * density).coerceAtLeast(3f),
                (rect.left + paint.measureText(label) + 19 * density).coerceAtMost(width.toFloat()),
                (rect.top - 1 * density).coerceAtLeast(26 * density))
            paint.style = Paint.Style.FILL
            paint.color = Color.rgb(17, 29, 31)
            canvas.drawRoundRect(tag, 5 * density, 5 * density, paint)
            paint.color = color
            canvas.drawText(label, tag.left + 8 * density, tag.bottom - 7 * density, paint)
        }
    }
}
