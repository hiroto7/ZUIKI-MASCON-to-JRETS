from main import get_notch, Notch


def test_get_notch() -> None:
    assert get_notch(1.0, False) == Notch.P5
    assert get_notch(0.8039185766167181, False) == Notch.P4
    assert get_notch(0.6156804101687674, False) == Notch.P3
    assert get_notch(0.43528550065614796, False) == Notch.P2
    assert get_notch(0.24704733420819727, False) == Notch.P1
    assert get_notch(0.003906369212927641, False) == Notch.N
    assert get_notch(-0.20786156804101688, False) == Notch.B1
    assert get_notch(-0.3176671651356548, False) == Notch.B2
    assert get_notch(-0.4274727622302927, False) == Notch.B3
    assert get_notch(-0.5294351023895993, False) == Notch.B4
    assert get_notch(-0.6392406994842372, False) == Notch.B5
    assert get_notch(-0.7490462965788751, False) == Notch.B6
    assert get_notch(-0.8510086367381817, False) == Notch.B7
    assert get_notch(-0.9608142338328196, False) == Notch.B8
    assert get_notch(-1.000030518509476, True) == Notch.EB
