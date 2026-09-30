package com.diamantmuqici.claritycam

import android.content.Context

/** Camera FPS / EV are requests to hardware; tonal changes affect OCR and saved photos. */
data class Tuning(
    val gamma: Float = 1f,
    val contrast: Float = 1.08f,
    val highlights: Float = .25f,
    val shadows: Float = .12f,
    val clarity: Float = .25f,
    val saturation: Float = 1f,
    val denoise: Int = 0,
    val fps: Int = 0, // 0 auto, 30/60 only when camera declares a matching range
    val exposureIndex: Int = 0,
    val scanMode: ScanMode = ScanMode.PLATE,
    val autoSnap: Boolean = true,
    val autoZoom: Float = 2f,
) {
    companion object {
        fun load(context: Context): Tuning {
            val p = context.getSharedPreferences("clarity_v2", Context.MODE_PRIVATE)
            return Tuning(
                gamma = p.getFloat("gamma", 1f).coerceIn(.6f, 1.8f),
                contrast = p.getFloat("contrast", 1.08f).coerceIn(.7f, 1.5f),
                highlights = p.getFloat("highlights", .25f).coerceIn(0f, .8f),
                shadows = p.getFloat("shadows", .12f).coerceIn(0f, .6f),
                clarity = p.getFloat("clarity", .25f).coerceIn(0f, 1f),
                saturation = p.getFloat("saturation", 1f).coerceIn(.6f, 1.5f),
                denoise = p.getInt("denoise", 0).coerceIn(0, 3),
                fps = p.getInt("fps", 0).let { if (it in listOf(0, 30, 60)) it else 0 },
                exposureIndex = p.getInt("exposure", 0),
                scanMode = if (p.getString("mode", "PLATE") == "TEXT") ScanMode.TEXT else ScanMode.PLATE,
                autoSnap = p.getBoolean("auto", true),
                autoZoom = p.getFloat("autoZoom", 2f).coerceIn(1.5f, 4f),
            )
        }
    }

    fun save(context: Context) {
        context.getSharedPreferences("clarity_v2", Context.MODE_PRIVATE).edit()
            .putFloat("gamma", gamma).putFloat("contrast", contrast)
            .putFloat("highlights", highlights).putFloat("shadows", shadows)
            .putFloat("clarity", clarity).putFloat("saturation", saturation)
            .putInt("denoise", denoise).putInt("fps", fps)
            .putInt("exposure", exposureIndex).putString("mode", scanMode.name)
            .putBoolean("auto", autoSnap).putFloat("autoZoom", autoZoom).apply()
    }
}
