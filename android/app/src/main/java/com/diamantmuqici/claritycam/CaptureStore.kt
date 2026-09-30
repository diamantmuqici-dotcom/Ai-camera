package com.diamantmuqici.claritycam

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Both captures are written to the system photo library, with no storage/cloud permission. */
object CaptureStore {
    fun save(context: Context, originalJpeg: ByteArray, rotation: Int, mirror: Boolean,
             tuning: Tuning): Uri {
        val enhancedJpeg = DetailEngine.enhancedJpeg(originalJpeg, rotation, mirror, tuning)
        val name = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val enhanced = insert(context, "CLARITY_${name}_enhanced.jpg", enhancedJpeg)
        return try {
            insert(context, "CLARITY_${name}_original.jpg", originalJpeg)
            enhanced
        } catch (e: Exception) {
            context.contentResolver.delete(enhanced, null, null)
            throw e
        }
    }

    private fun insert(context: Context, filename: String, bytes: ByteArray): Uri {
        val resolver = context.contentResolver
        val data = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, filename)
            put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
            put(MediaStore.Images.Media.RELATIVE_PATH, "${Environment.DIRECTORY_PICTURES}/ClarityCam")
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }
        val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, data)
            ?: error("Could not create photo in Pictures/ClarityCam")
        try {
            resolver.openOutputStream(uri)?.use { it.write(bytes) }
                ?: error("Could not write photo to storage")
            resolver.update(uri, ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) },
                null, null)
            return uri
        } catch (error: Exception) {
            resolver.delete(uri, null, null)
            throw error
        }
    }
}
