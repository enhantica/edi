"""Exact published delivery and shared-SDK producer boundaries."""

# Calendar routes are the published v2026.11.14 contract (ADRs 0071/0072).
# Native and SDK transport extend those routes under ADR 0083.
ROUTES = {
    ('ci.yml', 'native', 'edi-native-${{ matrix.sdk }}'): (
        {'build/edi-native-artifact'},
        ('pixi run core-build', 'tools/ci/edi_native.py pack --out build/edi-native-artifact'),
    ),
    ('crysta-sdk.yml', 'build', 'crysta-sdk-${{ matrix.platform }}'): (
        {'crysta-sdk-archives'},
        ('cpp-ci sdk-pack', 'SDK checksum does not bind the requested archive'),
    ),
    ('installers.yml', 'installers', 'installer-${{ runner.os }}-${{ github.run_attempt }}'): (
        {'build/installer/delivery'},
        (
            'tools/installer/build.py',
            'offline-qualification.json',
            'qualification.json',
            'pack_components(',
        ),
    ),
    (
        'installers.yml',
        'installers',
        'installer-components-${{ runner.os }}-${{ github.run_attempt }}',
    ): (
        {'build/installer/components'},
        (
            'tools/installer/build.py',
            'package.py" package --kind online',
            "'--repository'",
            'pack_components(',
        ),
    ),
    (
        'installers.yml',
        'installers',
        'installer-check-${{ runner.os }}-${{ github.run_attempt }}',
    ): (
        {
            'build/installer/assistant-lifetime.xml',
            'build/installer/project-retirement.xml',
            'build/installer/test/*.log',
            'build/installer/test/*.json',
            'build/installer/test/smoke/**',
            'build/installer/online-test/*.log',
            'build/installer/online-test/*.json',
            'build/installer/online-test/smoke/**',
            'build/installer/online-assistant-test/*.log',
            'build/installer/online-assistant-test/*.json',
            'build/installer/online-assistant-test/smoke/**',
            'build/installer/online/installer.json',
            'build/installer/stage/bundle-audit.json',
            'build/installer/protocol/*.log',
            'build/installer/protocol/passed.json',
            'build/installer/package/installer.json',
        },
        (
            'check_process_lifetime.py',
            'project-retirement.xml',
            'tools/installer/package.py" test',
        ),
    ),
    ('installers.yml', 'qualify-release', 'qualified-release-plan-${{ github.run_attempt }}'): (
        {'release-plan'},
        ('tools/release/download_plan.py', '--run "$PREPARE_RUN" --output release-plan'),
    ),
    ('release-plan.yml', 'plan', 'release-plan-${{ github.run_attempt }}'): (
        {'release-plan'},
        ('tools/release/prepare.py --repo "$GITHUB_REPOSITORY" --output release-plan',),
    ),
    ('pages.yml', 'docs', 'pages-docs'): (
        {'site'},
        (
            'pixi run pages-check',
            'pixi run notebooks-run',
            'pixi run site-build --require-outputs',
            'cp -R website/_build/. site/',
        ),
    ),
    ('pages.yml', 'wasm', 'pages-webapp'): (
        {'build/wasm/site'},
        ('pixi run -e app wasm-toolchain', 'pixi run -e app --skip-deps wasm-build'),
    ),
    ('release-publish.yml', 'publish', 'offsite-${{ github.run_attempt }}'): (
        {'copies/offsite'},
        (
            'tools/release/promote.py',
            'tools/release/webapp_archive.py',
            'tools/release/distribution.py --publication publication --output copies',
        ),
    ),
}


def enabled(step):
    return str(step.get('continue-on-error', 'false')).lower() != 'true' and step.get('if') in {
        None,
        'success()',
        '${{ success() }}',
        "steps.cache.outputs.cache-hit != 'true'",
    }


def reviewed_delivery(filename, name, job, upload):
    options = upload.get('with', {})
    key = filename, name, options.get('name')
    if key not in ROUTES:
        return False
    paths, proofs = ROUTES[key]
    if set(options.get('path', '').splitlines()) != paths:
        return False
    ordinary = upload.get('if') in {None, 'success()', '${{ success() }}'}
    diagnostic = upload.get('if') == 'always()' and options['name'].startswith('installer-check-')
    if (
        not (ordinary or diagnostic)
        or str(upload.get('continue-on-error', 'false')).lower() == 'true'
    ):
        return False
    if sum(step.get('with', {}).get('name') == options['name'] for step in job['steps']) != 1:
        return False
    before = job['steps'][: job['steps'].index(upload)]
    programs = [
        '\n'.join(
            line for line in step.get('run', '').splitlines() if not line.lstrip().startswith('#')
        )
        for step in before
        if enabled(step)
        and (filename == 'crysta-sdk.yml' or 'cache-hit' not in step.get('if', ''))
    ]
    return all(
        any(proof in program for program in programs) for proof in proofs
    ) and job_admission(filename, name, job)


def job_admission(filename, name, job):
    if name == 'native':
        from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415 - avoid import cycle
            producer_boundary,
        )

        try:
            producer_boundary(job)
        except AssertionError:
            return False
    if (filename, name) == ('installers.yml', 'qualify-release'):
        return job.get(
            'needs'
        ) == 'installers' and "needs.installers.result == 'success'" in job.get('if', '')
    if filename == 'release-publish.yml':
        terms = {term.strip() for term in job.get('if', '').split('&&')}
        return terms == {
            "github.ref == 'refs/heads/main'",
            "github.repository == 'enhantica/edi'",
            'github.event.pull_request.head.repo.fork == false',
        }
    return True
