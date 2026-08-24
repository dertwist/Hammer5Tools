#ifndef HAMMER5TOOLS_NATIVE_H
#define HAMMER5TOOLS_NATIVE_H

#include <stdint.h>

#if defined(_WIN32)
#define H5T_API __declspec(dllimport)
#else
#define H5T_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

H5T_API int32_t h5t_core_abi_version(void);

H5T_API int32_t h5t_smartprop_evaluate_json(
    const uint8_t* document,
    int32_t document_length,
    const uint8_t* nested_documents,
    int32_t nested_documents_length,
    int32_t maximum_depth,
    int32_t maximum_models,
    int64_t cancellation_id,
    uint8_t** output,
    int32_t* output_length);

H5T_API int32_t h5t_smartprop_evaluate_expression(
    const uint8_t* request,
    int32_t request_length,
    uint8_t** output,
    int32_t* output_length);

H5T_API int32_t h5t_smartprop_serialize_json(
    const uint8_t* document,
    int32_t document_length,
    uint8_t** output,
    int32_t* output_length);

H5T_API int32_t h5t_smartprop_deserialize_text(
    const uint8_t* text,
    int32_t text_length,
    uint8_t** output,
    int32_t* output_length);

H5T_API void h5t_core_release(void* memory);
H5T_API int64_t h5t_core_create_cancellation(void);
H5T_API int32_t h5t_core_cancel(int64_t cancellation_id);
H5T_API void h5t_core_release_cancellation(int64_t cancellation_id);

#ifdef __cplusplus
}
#endif

#endif
