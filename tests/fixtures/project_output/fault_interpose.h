#ifndef EDI_OUTPUT_FAULT_INTERPOSE_H
#define EDI_OUTPUT_FAULT_INTERPOSE_H

#ifdef __APPLE__
#define DYLD_INTERPOSE(_replacement, _replacee) \
    __attribute__((used)) static struct { const void* replacement; const void* replacee; } _interpose_##_replacee \
        __attribute__((section("__DATA,__interpose"))) = {(const void*)(unsigned long)&_replacement, (const void*)(unsigned long)&_replacee};
#define FAULT(name) edi_output_fault_##name
#define REAL(name) (&name)
#define INTERPOSE(name) DYLD_INTERPOSE(FAULT(name), name)
#else
#define FAULT(name) name
#define REAL(name) dlsym(RTLD_NEXT, #name)
#define INTERPOSE(name)
#endif

#endif
