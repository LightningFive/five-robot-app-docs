#pragma once
#include <stdint.h>
// API 2.17. Raw RFC 6716 packets, not Ogg. One optional half-duplex codec.
// All input is copied; no APP memory is accessed by the worker. No audio lease
// is acquired here: use the existing PCM capture/play APIs at the stated rate.
// Two outstanding frames TOTAL (queued + processing + unread), BUSY on full;
// never silently discard. Read returns header + actual payload bytes, 0 pending.
#define X622_OPUS_CONFIG_VERSION 1u
#define X622_OPUS_CONFIG_COMPACT_VERSION 2u
#define X622_OPUS_LOW_DELAY 1u
#define X622_OPUS_PREPARE_CORE 2u
#define X622_OPUS_ENCODE 1u
#define X622_OPUS_DECODE 2u
#define X622_OPUS_QUEUE_FRAMES 2u
#define X622_OPUS_PACKET_MAX 1275u
#define X622_OPUS_PCM_MAX 2880u
#define X622_OPUS_STARTING 1u
#define X622_OPUS_READY 2u
#define X622_OPUS_BUSY 3u
#define X622_OPUS_CLOSING 4u
#define X622_OPUS_FAILED 5u
typedef struct {
    uint32_t version, size, direction, sample_rate;
    // Mono PCM16 LE only. Encode: 16000 Hz, 6000..32000 bps; decode: 16/24 kHz,
    // bitrate=0. Duration 20/40/60 ms. Decode rejects larger output, no realloc.
    uint32_t frame_ms, bitrate, queue_frames, reserved;
} x622_opus_config_t; // 32 bytes
// V1 behavior is unchanged. Opt-in V2: queue_frames=1..2, frame-sized owned
// slots; reserved=LOW_DELAY for standard-Opus CELT-only wideband encoding
// (24 KiB worker, measured C3 stack peak17568 B, core about5.1KiB), or0 for
// VOIP/decoding. One slot applies backpressure until Read.
// V2 decoder worker12KiB (isolated C3 peak8076B); V1 remains20KiB.
// Without PREPARE_CORE, V2 LOW_DELAY/decoder queue, stack and opaque state
// share one 4KiB-rounded work block (one-slot 16kHz:36KiB). Stop returns the
// complete block after worker join. No retained pool or hidden idle worker.
// V2 Read accepts capacity >=32+1275 for encode or32+PCM bytes for decode.
// PREPARE_CORE can be ORed into reserved: initialize the codec, then release
// its bootstrap task/stack while keeping the codec state until Submit or Stop.
// Submit lazily recreates a worker and can return NO_MEMORY without consuming
// the frame. This lets APPs prepare large codec state before Wi-Fi/TLS starts.
// The returned prefix and status ABI remain identical. No silent drops/realloc.
typedef struct {
    uint32_t generation, sequence, direction, sample_rate;
    uint32_t frame_ms, payload_bytes;
    int32_t error, codec_error;
    uint8_t payload[X622_OPUS_PCM_MAX];
} x622_opus_result_t; // 2912 bytes; valid returned prefix is 32+payload_bytes
typedef struct {
    uint32_t generation, state, direction, sample_rate, frame_ms;
    int32_t last_error, codec_error;
    uint32_t submitted, completed, failed, queued_jobs, queued_results;
    uint32_t last_job_us, max_job_us, worker_stack_min, owned_bytes;
} x622_opus_status_t; // 64 bytes; owned_bytes includes V2 work block, excludes external vendor allocations
// Start returns positive generation immediately; poll status until READY.
// Stop accepts cancellation immediately. Subsequent Start may return BUSY until
// the stopped worker is reaped. APP exit joins and wipes all queues/codec state.
