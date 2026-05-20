package app.adblocker.vpn

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * DNS over UDP の最小パーサ/ビルダ。
 *
 * 仕様: RFC 1035。クエリの最初の質問セクションからドメイン名を取得し、
 * 同じトランザクション ID で NXDOMAIN 応答を組み立てる用途のみをサポートする。
 */
object DnsPacket {

    /** クエリ本体 (UDP ペイロード) から最初の質問のドメイン名を取り出す。失敗時は null。 */
    fun firstQuestionName(payload: ByteArray, offset: Int, length: Int): String? {
        if (length < 12) return null
        val qdCount = readU16(payload, offset + 4)
        if (qdCount < 1) return null
        return readName(payload, offset + 12, offset + length)?.first
    }

    /**
     * 入力クエリに対応する NXDOMAIN 応答 (UDP ペイロード) を組み立てる。
     * ID とクエリ部はそのままエコーする。
     */
    fun buildNxDomainResponse(query: ByteArray, offset: Int, length: Int): ByteArray? {
        if (length < 12) return null
        // クエリ末尾位置 (question section の終端) を求める
        val qEnd = scanQuestionEnd(query, offset, length) ?: return null
        val out = ByteArray(qEnd - offset)
        System.arraycopy(query, offset, out, 0, out.size)
        // Flags: QR=1, Opcode=copied, AA=0, TC=0, RD=copied, RA=1, Z=0, RCODE=3 (NXDOMAIN)
        val rd = (out[2].toInt() and 0x01)
        out[2] = ((0x80) or (out[2].toInt() and 0x78) or rd).toByte()
        out[3] = ((0x80) or 0x03).toByte()
        // ANCOUNT / NSCOUNT / ARCOUNT = 0
        out[6] = 0; out[7] = 0
        out[8] = 0; out[9] = 0
        out[10] = 0; out[11] = 0
        return out
    }

    private fun scanQuestionEnd(buf: ByteArray, offset: Int, length: Int): Int? {
        val end = offset + length
        var p = offset + 12
        val qd = readU16(buf, offset + 4)
        repeat(qd) {
            val nameEnd = skipName(buf, p, end) ?: return null
            p = nameEnd
            if (p + 4 > end) return null
            p += 4 // QTYPE + QCLASS
        }
        return p
    }

    private fun readU16(buf: ByteArray, p: Int): Int =
        ((buf[p].toInt() and 0xFF) shl 8) or (buf[p + 1].toInt() and 0xFF)

    /** 圧縮ポインタも辿りながらドメイン名を組み立てる。返り値: (名前, クエリ内でこの名前が占める末尾位置) */
    private fun readName(buf: ByteArray, start: Int, end: Int): Pair<String, Int>? {
        val sb = StringBuilder()
        var p = start
        var jumped = false
        var afterPointer = -1
        var safety = 0
        while (p < end) {
            if (safety++ > 255) return null
            val len = buf[p].toInt() and 0xFF
            if (len == 0) {
                p++
                if (!jumped) afterPointer = p
                break
            }
            if ((len and 0xC0) == 0xC0) {
                if (p + 1 >= end) return null
                if (!jumped) afterPointer = p + 2
                val off = ((len and 0x3F) shl 8) or (buf[p + 1].toInt() and 0xFF)
                p = off
                jumped = true
                continue
            }
            if ((len and 0xC0) != 0) return null // 未知ラベルタイプ
            p++
            if (p + len > end) return null
            if (sb.isNotEmpty()) sb.append('.')
            for (i in 0 until len) {
                sb.append((buf[p + i].toInt() and 0xFF).toChar())
            }
            p += len
        }
        if (afterPointer == -1) return null
        return Pair(sb.toString().lowercase(), afterPointer)
    }

    /** 名前の終端 (次フィールド開始位置) を返す。圧縮ポインタは 2 バイトとして扱う。 */
    private fun skipName(buf: ByteArray, start: Int, end: Int): Int? {
        var p = start
        var safety = 0
        while (p < end) {
            if (safety++ > 255) return null
            val len = buf[p].toInt() and 0xFF
            if (len == 0) return p + 1
            if ((len and 0xC0) == 0xC0) {
                return if (p + 2 <= end) p + 2 else null
            }
            if ((len and 0xC0) != 0) return null
            p += 1 + len
        }
        return null
    }

    /** デバッグ用: バイト列を 16 進文字列に。 */
    fun hex(b: ByteArray, off: Int = 0, len: Int = b.size): String {
        val bb = ByteBuffer.wrap(b, off, len).order(ByteOrder.BIG_ENDIAN)
        val sb = StringBuilder(len * 2)
        while (bb.hasRemaining()) sb.append("%02x".format(bb.get().toInt() and 0xFF))
        return sb.toString()
    }
}
