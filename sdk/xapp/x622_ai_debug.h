#pragma once
#include "x622_xapp.h"

/* Optional pure-header helpers, using the EXISTING log import. No ABI/memory
 * setting changes. Captured only when this AI-delivered app is explicitly tried
 * from its own conversation. Never include passwords, tokens or raw audio.
 * Persistent per-app storage APIs remain the authority for normal app saves.
 * This small diagnostic snapshot is not an arbitrary file-export mechanism.
 */
static inline int32_t x622_ai_debug(const char* text,uint32_t bytes) {
    return text&&bytes<=480?x622_log(text,bytes):X622_ERR_INVALID_ARGUMENT;
}
static inline int32_t x622_ai_save_state(const char* text,uint32_t bytes) {
    char line[512];uint32_t i;
    const char prefix[]="[AI_STATE] ";
    if(!text||bytes>480)return X622_ERR_INVALID_ARGUMENT;
    for(i=0;i<11;i++)line[i]=prefix[i];
    for(i=0;i<bytes;i++)line[11+i]=text[i];
    return x622_log(line,11+bytes);
}
