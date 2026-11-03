# Output failure probes

Run from the checkout with the ordinary runner user and a native C compiler:

```sh
python3 tests/fixtures/project_output/platform_probe.py > platform-probe.jsonl
```

No app build, import, SDK or sibling checkout is needed. The script compiles a small
native caller and the existing visible fault libraries, then prints JSON observations.
Compilation and child-launch errors stop the probe. A launched child's exit status,
stderr and syscall outcomes are observations, not pass/fail judgments. Keep stdout
and stderr in the workflow artifact.

The permission probes use only fresh entries in a temporary directory. They restore
permissions and the user immutable flag before cleanup. Run without sudo: an effective
root user cannot demonstrate the mode-bit refusal. ACLs can also change the result.

Expected filesystem observations on ordinary Linux and macOS runners:

- A directory set to 0555 denies unlink and replacement within that directory with EACCES.
- Replacing a hard or symbolic file link in a writable directory succeeds, retaining the
  outside target's bytes. Holding the old regular file open, or setting it to 0444,
  does not prevent replacement; the open descriptor retains the old bytes.
- Renaming a regular file onto a directory fails with EISDIR.
- macOS user immutable (`uchg`) prevents deletion and replacement with EPERM. Linux's
  Python has no corresponding `os.chflags` operation; this is reported as unavailable.

The loader probes run each primitive without injection and with the gate's library
inserted. Linux uses LD_PRELOAD; macOS uses dyld's interposition section, following
the existing `scan_app/io_faults.cpp` witness. Both must activate the matching fault
and emit its receipt. The extra macOS `flat` run checks that setting
DYLD_FORCE_FLAT_NAMESPACE does not change that result. The temporary-file witness
also probes Darwin's three additional rename entry points; its receipt names the
entry point actually reached.
Each library includes a constructor stamp so that loading and hook activation are
observed separately. An absent stamp suggests loader rejection or environment loss;
a stamp without a fault receipt suggests a binding or matching problem.
Use the same compiler and Python as the failing runner; record their versions.

Apple's [interposition declaration and example](https://github.com/apple-oss-distributions/dyld/blob/main/include/mach-o/dyld-interposing.h)
call the original function directly from the replacement. The macOS witnesses do
the same, avoiding resolver calls inside low-level read/write replacements.

[Apple rename(2)](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/rename.2.html),
[Apple unlink(2)](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/unlink.2.html),
[Apple file flags](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/FileSystemDetails/FileSystemDetails.html),
[Apple dyld(1), version 852.2](https://github.com/apple-oss-distributions/dyld/blob/dyld-852.2/doc/man/man1/dyld.1),
[Linux rename(2)](https://man7.org/linux/man-pages/man2/rename.2.html),
[Linux ld.so(8)](https://man7.org/linux/man-pages/man8/ld.so.8.html).
