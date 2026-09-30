package com.diamantmuqici.claritycam

import java.text.Normalizer

/** A recognized text LINE with bounds, not proof that a registration plate exists. */
enum class ScanMode { PLATE, TEXT }

data class ScanBox(val left: Float, val top: Float, val right: Float, val bottom: Float) {
    fun intersectionOverUnion(other: ScanBox): Float {
        val w = (minOf(right, other.right) - maxOf(left, other.left)).coerceAtLeast(0f)
        val h = (minOf(bottom, other.bottom) - maxOf(top, other.top)).coerceAtLeast(0f)
        val area = (right - left) * (bottom - top) +
            (other.right - other.left) * (other.bottom - other.top) - w * h
        return if (area > 0f) w * h / area else 0f
    }
}

data class ScanTarget(val text: String, val bounds: ScanBox, val kind: ScanMode)

object PlateRules {
    private val characters = Regex("[A-Z0-9\\s-]+")
    fun key(text: String): String = Normalizer.normalize(text, Normalizer.Form.NFKC)
        .uppercase().filter { it in 'A'..'Z' || it in '0'..'9' }

    /** Conservative Latin plate candidate heuristic; never change an ambiguous O/0 or I/1. */
    fun isCandidate(text: String, aspect: Float): Boolean {
        val raw = Normalizer.normalize(text, Normalizer.Form.NFKC).uppercase().trim()
        if (!characters.matches(raw)) return false
        val normalized = key(raw)
        return normalized.length in 5..10 && aspect in 1.5f..12f &&
            normalized.count { it.isLetter() } >= 1 && normalized.count { it.isDigit() } >= 2
    }
}

/** Three consistent readings, focus and zoom gate, bounded history, per-text cooldown. */
class StableSnapper(private val hitsRequired: Int = 3, private val cooldownMs: Long = 18_000L) {
    private var previous: ScanTarget? = null
    private var hits = 0
    private var lastSeenAt: Long? = null
    private var lastAnyAt: Long? = null
    private val saved = LinkedHashMap<String, Long>()

    fun reset() { previous = null; hits = 0; lastSeenAt = null }

    fun observe(target: ScanTarget?, zoom: Float, minZoom: Float, focusScore: Float,
                nowMs: Long): Boolean {
        if (target == null || zoom < minZoom || focusScore < 5f) { reset(); return false }
        val key = PlateRules.key(target.text)
        if (key.isEmpty()) { reset(); return false }
        val same = previous?.let { PlateRules.key(it.text) == key &&
            it.bounds.intersectionOverUnion(target.bounds) >= .3f &&
            lastSeenAt?.let { at -> nowMs - at <= 2500L } == true } == true
        hits = if (same) hits + 1 else 1
        previous = target
        lastSeenAt = nowMs
        if (hits < hitsRequired) return false
        if (lastAnyAt?.let { nowMs - it < 5000L } == true ||
            saved[key]?.let { nowMs - it < cooldownMs } == true) return false
        hits = 0
        lastAnyAt = nowMs
        saved[key] = nowMs
        if (saved.size > 128) saved.entries.removeAll { nowMs - it.value > cooldownMs }
        return true
    }
}
