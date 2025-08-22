#include <stdlib.h>
#include <string.h>
#include <webrtc/modules/audio_processing/include/audio_processing.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    webrtc::AudioProcessing* apm;
    float erle;
    int frame;
    int rate;
} Aec3Ctx;

void* aec_init(int rate, int frame) {
    webrtc::AudioProcessing* apm = webrtc::AudioProcessingBuilder().Create();
    webrtc::AudioProcessing::Config config;
    config.echo_canceller.enabled = true;
    apm->ApplyConfig(config);
    apm->set_sample_rate_hz(rate);
    Aec3Ctx* ctx = (Aec3Ctx*)malloc(sizeof(Aec3Ctx));
    ctx->apm = apm;
    ctx->erle = 0.f;
    ctx->frame = frame;
    ctx->rate = rate;
    return ctx;
}

void aec_process(void* ptr, const int16_t* near, const int16_t* far, int16_t* out) {
    Aec3Ctx* ctx = (Aec3Ctx*)ptr;
    if (!ctx) return;
    webrtc::StreamConfig cfg(ctx->rate, 1);
    ctx->apm->ProcessRenderStream(far, cfg, cfg);
    memcpy(out, near, ctx->frame * sizeof(int16_t));
    ctx->apm->ProcessStream(out, cfg, cfg, out);
    ctx->erle = 20.f;  // placeholder
}

float aec_erle(void* ptr) {
    Aec3Ctx* ctx = (Aec3Ctx*)ptr;
    return ctx ? ctx->erle : 0.f;
}

void aec_free(void* ptr) {
    Aec3Ctx* ctx = (Aec3Ctx*)ptr;
    if (!ctx) return;
    delete ctx->apm;
    free(ctx);
}

#ifdef __cplusplus
}
#endif
