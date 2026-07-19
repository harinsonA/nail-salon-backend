from django.urls import path
from apps.tareas.views import TaskView, TaskListView

urlpatterns = [
    path(
        "procesos/",
        TaskView.as_view(),
        name="tasks",
    ),
    path(
        "procesos/lista/ajax",
        TaskListView.as_view(),
        name="task_list",
    ),
]
