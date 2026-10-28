// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#if defined(__linux__) && !defined(__EMSCRIPTEN__)
#include <sys/syscall.h>
#include <linux/fs.h>
#include <unistd.h>
#elif defined(__APPLE__)
#include <stdio.h>
#endif
namespace edi::detail {
// Shared native publication primitive (ADR-0056): fresh means no replacement;
// an existing owned-file exchange keeps its original caller's validation.
inline int atomic_publish(int sourceParent,const char* source,int targetParent,const char* target,bool exchange) noexcept {
#if defined(__linux__) && defined(SYS_renameat2) && !defined(__EMSCRIPTEN__)
    return static_cast<int>(::syscall(SYS_renameat2,sourceParent,source,targetParent,target,exchange?RENAME_EXCHANGE:RENAME_NOREPLACE));
#elif defined(__APPLE__)
    return ::renameatx_np(sourceParent,source,targetParent,target,exchange?RENAME_SWAP:RENAME_EXCL);
#else
    return -1;
#endif
}
} // namespace edi::detail
