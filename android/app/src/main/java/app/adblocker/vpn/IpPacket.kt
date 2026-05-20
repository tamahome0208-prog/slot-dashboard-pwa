package app.adblocker.vpn

/**
 * tun から取り出した生 IP パケットを操作するためのユーティリティ。
 * IPv4 / UDP の最小ケースのみ扱う (10.215.173.2:53 宛の DNS クエリ専用)。
 */
object IpPacket {

    const val PROTO_UDP: Byte = 17

    fun version(buf: ByteArray): Int = (buf[0].toInt() shr 4) and 0x0F
    fun ihlBytes(buf: ByteArray): Int = (buf[0].toInt() and 0x0F) * 4
    fun protocol(buf: ByteArray): Byte = buf[9]
    fun totalLength(buf: ByteArray): Int =
        ((buf[2].toInt() and 0xFF) shl 8) or (buf[3].toInt() and 0xFF)

    fun srcAddr(buf: ByteArray): IntArray = intArrayOf(
        buf[12].toInt() and 0xFF, buf[13].toInt() and 0xFF,
        buf[14].toInt() and 0xFF, buf[15].toInt() and 0xFF
    )

    fun dstAddr(buf: ByteArray): IntArray = intArrayOf(
        buf[16].toInt() and 0xFF, buf[17].toInt() and 0xFF,
        buf[18].toInt() and 0xFF, buf[19].toInt() and 0xFF
    )

    fun udpSrcPort(buf: ByteArray, ipHeaderLen: Int): Int =
        ((buf[ipHeaderLen].toInt() and 0xFF) shl 8) or (buf[ipHeaderLen + 1].toInt() and 0xFF)

    fun udpDstPort(buf: ByteArray, ipHeaderLen: Int): Int =
        ((buf[ipHeaderLen + 2].toInt() and 0xFF) shl 8) or (buf[ipHeaderLen + 3].toInt() and 0xFF)

    fun udpPayloadOffset(ipHeaderLen: Int): Int = ipHeaderLen + 8

    fun udpPayloadLength(buf: ByteArray, ipHeaderLen: Int): Int {
        val udpLen = ((buf[ipHeaderLen + 4].toInt() and 0xFF) shl 8) or
                (buf[ipHeaderLen + 5].toInt() and 0xFF)
        return (udpLen - 8).coerceAtLeast(0)
    }

    /**
     * 応答パケットを組み立てる。
     * - 入力 [requestPacket] (受信した IPv4 + UDP + DNS クエリ) の src/dst を入れ替える
     * - UDP ペイロードを [responsePayload] に差し替える
     * - IP/UDP ヘッダのチェックサムを再計算
     */
    fun buildReply(
        requestPacket: ByteArray,
        requestLength: Int,
        responsePayload: ByteArray
    ): ByteArray {
        val ihl = ihlBytes(requestPacket)
        val out = ByteArray(ihl + 8 + responsePayload.size)
        // IP ヘッダをコピー
        System.arraycopy(requestPacket, 0, out, 0, ihl)
        // src/dst アドレスを入れ替え
        for (i in 0 until 4) {
            val tmp = out[12 + i]
            out[12 + i] = out[16 + i]
            out[16 + i] = tmp
        }
        // total length
        val totalLen = out.size
        out[2] = ((totalLen shr 8) and 0xFF).toByte()
        out[3] = (totalLen and 0xFF).toByte()
        // identification / flags はリクエストから引き継いで OK
        // TTL を 64 にリセット
        out[8] = 64
        // header checksum をゼロ化して再計算
        out[10] = 0; out[11] = 0
        val ipChecksum = checksum(out, 0, ihl)
        out[10] = ((ipChecksum shr 8) and 0xFF).toByte()
        out[11] = (ipChecksum and 0xFF).toByte()

        // UDP ヘッダ: ポートを入れ替え
        val srcPort = udpSrcPort(requestPacket, ihl)
        val dstPort = udpDstPort(requestPacket, ihl)
        out[ihl + 0] = ((dstPort shr 8) and 0xFF).toByte()
        out[ihl + 1] = (dstPort and 0xFF).toByte()
        out[ihl + 2] = ((srcPort shr 8) and 0xFF).toByte()
        out[ihl + 3] = (srcPort and 0xFF).toByte()
        val udpLen = 8 + responsePayload.size
        out[ihl + 4] = ((udpLen shr 8) and 0xFF).toByte()
        out[ihl + 5] = (udpLen and 0xFF).toByte()
        out[ihl + 6] = 0; out[ihl + 7] = 0 // checksum: 0 で省略可 (IPv4)

        // ペイロード
        System.arraycopy(responsePayload, 0, out, ihl + 8, responsePayload.size)

        // UDP チェックサム (擬似ヘッダ付き)
        val udpChecksum = udpChecksum(out, ihl)
        out[ihl + 6] = ((udpChecksum shr 8) and 0xFF).toByte()
        out[ihl + 7] = (udpChecksum and 0xFF).toByte()

        return out
    }

    private fun checksum(buf: ByteArray, offset: Int, length: Int): Int {
        var sum = 0
        var i = offset
        val end = offset + length
        while (i + 1 < end) {
            sum += ((buf[i].toInt() and 0xFF) shl 8) or (buf[i + 1].toInt() and 0xFF)
            if ((sum and 0xFFFF0000.toInt()) != 0) sum = (sum and 0xFFFF) + 1
            i += 2
        }
        if (i < end) {
            sum += (buf[i].toInt() and 0xFF) shl 8
            if ((sum and 0xFFFF0000.toInt()) != 0) sum = (sum and 0xFFFF) + 1
        }
        return sum.inv() and 0xFFFF
    }

    private fun udpChecksum(packet: ByteArray, ipHeaderLen: Int): Int {
        val udpLen = ((packet[ipHeaderLen + 4].toInt() and 0xFF) shl 8) or
                (packet[ipHeaderLen + 5].toInt() and 0xFF)
        var sum = 0
        // 擬似ヘッダ: src(4) + dst(4) + zero(1) + proto(1) + udpLen(2)
        for (i in 12..18 step 2) {
            sum += ((packet[i].toInt() and 0xFF) shl 8) or (packet[i + 1].toInt() and 0xFF)
        }
        sum += (PROTO_UDP.toInt() and 0xFF)
        sum += udpLen
        // UDP 全体
        var i = ipHeaderLen
        val end = ipHeaderLen + udpLen
        while (i + 1 < end) {
            sum += ((packet[i].toInt() and 0xFF) shl 8) or (packet[i + 1].toInt() and 0xFF)
            i += 2
        }
        if (i < end) sum += (packet[i].toInt() and 0xFF) shl 8
        while ((sum shr 16) != 0) sum = (sum and 0xFFFF) + (sum shr 16)
        val result = sum.inv() and 0xFFFF
        return if (result == 0) 0xFFFF else result
    }
}
