#pragma once
#include "x622_net.h"
#include "x622_http_headers.h"

/* API 2.17 candidate. Additive: ws_open keeps its API2.16 behavior.
 * ws_open_ex accepts ws:// and wss://. WSS always uses system CA validation
 * and the original hostname/SNI; never downgrades or follows redirects.
 * One WSS connection at a time. No other IP session may be active when a new
 * WSS handshake starts. After OPEN, existing numeric/cached-host rules apply.
 * Outer and transport descriptors version=1, size=sizeof; reserved=0.
 * All other queue/fragment/close rules are inherited from x622_net.h.
 */
#define X622_WS_CLEARTEXT_AUTH 1u
typedef struct {
    uint32_t version,size,flags,reserved;
    x622_ws_config_t transport;
    x622_http_headers_t headers;
} x622_ws_config_ex_t;

#define X622_WS_STAGE_DNS 1u
#define X622_WS_STAGE_CONNECT 2u
#define X622_WS_STAGE_TLS 3u
#define X622_WS_STAGE_UPGRADE 4u
#define X622_WS_STAGE_STREAM 5u
typedef struct {
    x622_net_status_t net;
    uint32_t stage;
    int32_t tls_error;
    uint32_t certificate_flags;
    int32_t upgrade_status;
} x622_ws_status_ex_t; /* 64 bytes. No secrets, hostnames or payload echoed. */
