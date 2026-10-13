"""Independent identities of the upstream GUI archive selected by ADR-0015.

The archive SHA-256 was measured from GitHub's cached commit archive. The source
digest sums sorted relative src/ paths and their SHA-256 values from that archive,
independently of the product's CMake declarations.
"""

PIN = '3897d339b60f5707bfe952fed59a20f73340e236'
ARCHIVE_SHA256 = '3aebde35ff5f714f83b5f76c03e4a54d40a84c196d766f020d6ce4eb683200e1'
SOURCE_SHA256 = '5e6ee5d998c030c0517a0b8adb19f13d22f63e1ea8c199bb5ec2076081db5888'
