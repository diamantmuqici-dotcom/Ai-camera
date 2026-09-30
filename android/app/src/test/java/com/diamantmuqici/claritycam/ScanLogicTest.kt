package com.diamantmuqici.claritycam

import org.junit.Assert.*
import org.junit.Test

class ScanLogicTest {
    @Test fun plateCandidatesAreConservativeAndDoNotGuessCharacters() {
        assertTrue(PlateRules.isCandidate("RKS 1234", 3.2f))
        assertTrue(PlateRules.isCandidate("AB-123-CD", 4f))
        assertFalse(PlateRules.isCandidate("WELCOME", 3f))
        assertFalse(PlateRules.isCandidate("123456", 3f))
        assertFalse(PlateRules.isCandidate("AB@123", 3f))
        assertFalse(PlateRules.isCandidate("RKS 1234", .8f))
        assertEquals("O0I1", PlateRules.key("O0 I1"))
    }

    @Test fun overlapIsRealIntersectionNotCenterDistance() {
        val box = ScanBox(.1f, .1f, .4f, .3f)
        assertEquals(1f, box.intersectionOverUnion(box), .0001f)
        assertEquals(0f, box.intersectionOverUnion(ScanBox(.6f, .1f, .9f, .3f)), .0001f)
    }

    @Test fun autoShutterNeedsStableFocusZoomAndCooldown() {
        val snap = StableSnapper()
        val a = ScanTarget("RKS 1234", ScanBox(.2f, .3f, .5f, .45f), ScanMode.PLATE)
        val b = a.copy(text = "AB 5678")
        assertFalse(snap.observe(a, 1f, 2f, 10f, 0))
        assertFalse(snap.observe(a, 2f, 2f, 2f, 200))
        assertFalse(snap.observe(a, 2f, 2f, 10f, 500))
        assertFalse(snap.observe(a, 2f, 2f, 10f, 1000))
        assertTrue(snap.observe(a, 2f, 2f, 10f, 1500))
        assertFalse(snap.observe(a, 2f, 2f, 10f, 2000))
        assertFalse(snap.observe(b, 2f, 2f, 10f, 3500))
        assertFalse(snap.observe(b, 2f, 2f, 10f, 4500))
        assertTrue(snap.observe(b, 2f, 2f, 10f, 6500)) // 5 s after last capture
        assertFalse(snap.observe(a, 2f, 2f, 10f, 18000))
        assertFalse(snap.observe(a, 2f, 2f, 10f, 18500))
        assertTrue(snap.observe(a, 2f, 2f, 10f, 20000))
    }
}
