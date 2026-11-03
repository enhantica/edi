"""Invoke the public Python report operations in a fault-isolated process."""

import sys

import edi

project = edi.Project.load(sys.argv[2])
if sys.argv[1] == 'core-save':
    project.report.save()
else:
    project.report.save_html(offline=False)
