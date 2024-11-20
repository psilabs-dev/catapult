from catapult import utils

def test_mask_string():

    assert '' == utils.mask_string('')
    assert '*' == utils.mask_string('1')
    assert '**' == utils.mask_string('12')
    assert 'h*********d' == utils.mask_string('hello world')

def test_coalesce():
    assert utils.coalesce('a', None, 'b') == 'a'
    assert utils.coalesce(None, None, None) is None
    assert utils.coalesce(None, 'a', 'b') == 'a'
    assert utils.coalesce('a', None, None) == 'a'
