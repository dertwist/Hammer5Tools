"""Element IDs must stay unique within a document.

The module-level functions used to be a second, unsynchronised copy of
ElementIDGenerator. They now delegate to one shared generator, so these cover
both the class and the fact that the functions really do share state.
"""

from gui.widgets import element_id as eid


def test_generators_are_independent():
    a, b = eid.ElementIDGenerator(), eid.ElementIDGenerator()
    first = a.update_value({'_class': 'x'})['m_nElementID']
    second = b.update_value({'_class': 'x'})['m_nElementID']
    # Separate documents allocate from separate spaces, so they may well collide.
    assert first == second == 1
    assert a.get_last_id() == b.get_last_id() == 1


def test_ids_are_unique_within_one_generator():
    gen = eid.ElementIDGenerator()
    ids = [gen.update_value({'_class': 'x'}, force=True)['m_nElementID'] for _ in range(50)]
    assert len(set(ids)) == 50
    assert 0 not in ids


def test_existing_id_is_preserved_and_registered():
    gen = eid.ElementIDGenerator()
    assert gen.update_value({'_class': 'x', 'm_nElementID': 7}) == {'_class': 'x', 'm_nElementID': 7}
    # 7 is now taken, so the next allocation must not reuse it.
    assert gen.update_value({'_class': 'y'}, force=True)['m_nElementID'] == 8


def test_get_key_does_not_burn_an_id_when_one_is_present():
    """The old free function passed set_element_id(force=True) as a .get() default,
    so it advanced the counter on every read. The generator only allocates when
    the key is actually missing."""
    gen = eid.ElementIDGenerator()
    before = gen.current_id()
    assert gen.get_key({'m_nElementID': 3}) == 3
    assert gen.current_id() == before


def test_get_key_allocates_when_missing():
    gen = eid.ElementIDGenerator()
    assert gen.get_key({}) == gen.current_id() != 0


def test_update_child_value_walks_nested_classes():
    gen = eid.ElementIDGenerator()
    tree = {'_class': 'root', 'm_Children': [{'_class': 'a'}, {'_class': 'b'}]}
    gen.update_child_value(tree, force=True)

    ids = [tree['m_nElementID']] + [c['m_nElementID'] for c in tree['m_Children']]
    assert len(set(ids)) == 3


def test_set_id_allocates_a_candidate_that_add_id_commits():
    """set_id proposes the next free id; until add_id registers it, asking again
    proposes the same one. update_value is the paired call that does both."""
    gen = eid.ElementIDGenerator()
    assert gen.set_id(force=True) == gen.set_id(force=True) == 1
    gen.add_id(1)
    assert gen.set_id(force=True) == 2


def test_module_functions_share_one_generator():
    eid.reset_element_id()
    first = eid.update_value_element_id({'_class': 'x'}, force=True)['m_nElementID']
    second = eid.update_value_element_id({'_class': 'y'}, force=True)['m_nElementID']
    assert second > first
    assert eid.get_element_id_last() == second


def test_reset_clears_the_shared_state():
    eid.set_element_id(force=True)
    eid.reset_element_id()
    assert eid.element_id() == 0
    assert eid.get_element_id_last() == 0
