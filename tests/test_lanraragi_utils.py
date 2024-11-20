from pathlib import Path

from catapult.lanraragi import utils

def test_calculate_sha1():
    expected_sha1 = 'a851751e1e14c39a78f0a4b8debf69dba0b2ae0d'
    actual_sha1 = utils.compute_sha1(Path('tests/resources/message.txt'))
    assert expected_sha1 == actual_sha1, 'Checksum mismatch'