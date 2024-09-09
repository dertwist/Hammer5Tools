class Properties:
    def __init__(self, tree, data=None):
        self.tree = tree
        self.data = data
        for index in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(index)
            if item.text(0) == 'Modifiers':
                print('Found item with name Modifiers:', item)
            if item.text(0) == 'ClassProperties':
                print('Found item with name ClassProperties:', item)
            if item.text(0) == 'SelectionCriteria':
                print('Found item with name SelectionCriteria:', item)