from catapult import utils

def test_mask_string():

    assert '' == utils.mask_string('')
    assert '*' == utils.mask_string('1')
    assert '**' == utils.mask_string('12')
    assert 'h*********d' == utils.mask_string('hello world')

def test_calculate_sha1():
    expected_sha1 = 'a851751e1e14c39a78f0a4b8debf69dba0b2ae0d'
    actual_sha1 = utils.calculate_sha1('tests/resources/message.txt')
    assert expected_sha1 == actual_sha1, 'Checksum mismatch'

def test_coalesce():
    assert utils.coalesce('a', None, 'b') == 'a'
    assert utils.coalesce(None, None, None) is None
    assert utils.coalesce(None, 'a', 'b') == 'a'
    assert utils.coalesce('a', None, None) == 'a'
