# Cranky User's Manual

Cranky is a command line tool that simplifies the process of developing Ubuntu
kernels. This guide is intended for those familiar with the Ubuntu kernel's
SRU workflow. Generally speaking, no programming knowledge is required to
use this tool. For precise instructions on how to crank a kernel, please
refer to the [cranking guide][1].

---

## Terminology

### Kernel Series

The central database for all kernel development, [kernel series][2], is both living
and volatile. This information is stored on a per-cycle basis to capture a
point-in-time reference of each kernel's development metadata. More generally,
this database expresses the kernel tree sets as a main package and its
dependent packages. All of these tree sets have specific attributes that cranky
will query during command invocation.

A tree set will use the kernel-series for the cycle listed in the main package's
$DEBIAN/tracking-bug file. It is not currently possible to use explicitly use
``info/kernel-series.yaml`` for cranky commands.

By default, cranky will read the latest per-cycle information published on
[kernel.ubuntu.com][4]. More information on this process can be found in the
[specification][5]. Cranky also supports reading from a local copy of this
information by setting the env ``KERNEL_SERIES_USE=local``. This requires that
you have cloned [kernel-versions][3] to ``info/kernel-versions``. Once cloned, 
you may modified the target cycle with the changes needed for your task. For
example, to test a change on 2023.07.10, you would modify 
``info/kernel-versions/2023.07.10/info/kernel-series.yaml``. Use this tree to
test your local changes before submitting a pull request to [kernel-versions][3].

For development, testing, and other changes that are not intended for production
you may use ``KERNEL_SERIES_USE=devel`` to read bypass cycle awareness and read
exclusively from your local ``info/kernel-series.yaml``.

### Handle

The basic unit of input that cranky requires is called a HANDLE. A HANDLE is a
flexible parameter that uniquely identifies a kernel and its dependent packages.
a HANDLE may be specified in one of three ways.

1. The standard form follows the pattern `series:package`. Series can be
   either the codename (e.g. bionic) or the literal series string in YY.MM format
   (e.g. 18.04). The package portion is always prefixed with linux and may be
   followed by a more specific derivative name, package type, or both. Primary
   kernels are typically referred to by `series:linux` and derivatives may look
   something like `series:linux-derivative`. When no package type is specified,
   such as -meta, then the main package is implied.

    Note: Specifying a standard handle without an explicit `--cycle` parameter
    will refer to the tip of kernel series.

2. The directory form is the path to a tree on disk. Only trees that have been
   checked out with `cranky checkout` may be used as handles of this form.

   Note: Specifying a standard handle without an explicit `--cycle` parameter
   will refer to the current cycle of _your checked out tree_. This is derived
   from the tracking-bug file of the tree set's main package. `cranky checkout`
   process transparently handles this relationship for packages that lack a
   tracking-bug file.

3. The absence of any handle implies the current working directory
   as the handle. The same rules of directory handles apply to this handle form.

### Cycle

A cycle, accepted by most cranky sub commands as `--cycle`, refers to the name 
of the SRU cycle being cranked. The format is [cdst]YYYY.MM.DD.

- An optional prefix:
  - c: an embargoed cycle
  - d: a development cycle
  - s: a security cycle
  - t: a testing cycle
- Year in the form YYYY
- Month in the form MM
- Day in the form DD

With the exception of development and testing cycles, the date will always fall
on a Monday. The oldest cycle that may be referenced is 2023.04.17 because that
is as far back as we have created snapshots for kernel-series in the
[kernel-versions][3] repository.

[1]: ../docs/cranking-the-kernel.md
[2]: ../../info/kernel-series.yaml
[3]: http://10.131.201.69/kernel/kernel-versions
[4]: https://kernel.ubuntu.com/info/
[5]: https://docs.google.com/document/d/1a7ZBCm1l2TmZSyGWQ30Q6mY0BBLauqXkQamxqwANZ_Y/edit
