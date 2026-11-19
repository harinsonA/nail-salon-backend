class ModelFeed:
    model = None

    def __init__(self, mark):
        self.mark = mark

    def alive(self):
        return self.model.objects.all()

    def items(self):
        alive = self.alive().order_by("pk")
        if self.mark.is_full:
            return alive
        return alive.filter(modified__gte=self.mark.changed_since)

    def removed(self):
        if self.mark.is_full:
            return []
        return list(
            self.model.all_objects.filter(modified__gte=self.mark.changed_since, is_removed=True)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
