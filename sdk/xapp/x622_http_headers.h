#pragma once
#include <stdint.h>

/* API 2.17 candidate. Shared HTTP/WS header block; existing ABI is unchanged.
 * version=1, size=sizeof, count<=8, bytes<=1024. data contains exactly count
 * name\0value\0 pairs, then zero padding. Names: 1..48 ASCII token bytes;
 * values: 0..512 visible ASCII bytes. No CR/LF, duplicate names (case-folded),
 * Host/Connection/Upgrade/framing/compression/Proxy-/Sec-WebSocket-* headers.
 * Authorization is allowed only under the transport's cleartext-auth policy.
 * No cookie jar, redirects, hardware secrets or credential persistence.
 * On enqueue the host copies only bytes, never retains a WASM pointer.
 */
typedef struct {
    uint32_t version, size, count, bytes;
    char data[1024];
} x622_http_headers_t;
