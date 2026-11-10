// SPDX-License-Identifier: BSD-3-Clause
// The browser build uses WasmFS (ADR-0030), whose link has no JavaScript socket library. Qt Core still references
// that library's six callback setters from its socket notifier support. The app opens no sockets, so the setters
// have nothing to register and do nothing.
#include <emscripten/emscripten.h>

void emscripten_set_socket_error_callback(void* /*userData*/, em_socket_error_callback /*callback*/) {}
void emscripten_set_socket_open_callback(void* /*userData*/, em_socket_callback /*callback*/) {}
void emscripten_set_socket_listen_callback(void* /*userData*/, em_socket_callback /*callback*/) {}
void emscripten_set_socket_connection_callback(void* /*userData*/, em_socket_callback /*callback*/) {}
void emscripten_set_socket_message_callback(void* /*userData*/, em_socket_callback /*callback*/) {}
void emscripten_set_socket_close_callback(void* /*userData*/, em_socket_callback /*callback*/) {}
