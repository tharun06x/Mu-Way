from django.db import models

class TaskCatalog(models.Model):
    task_name = models.CharField(max_length=255, unique=True, db_index=True)
    domain = models.CharField(max_length=100, null=True, blank=True)
    task_karma_value = models.IntegerField(default=0)
    difficulty_level = models.IntegerField(default=2)
    task_type = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.task_name

    class Meta:
        db_table = 'roadmap_taskcatalog'

class UserSubmission(models.Model):
    user_id = models.CharField(max_length=255, db_index=True)
    domain = models.CharField(max_length=100, null=True, blank=True)
    task_name = models.CharField(max_length=255)
    task_id = models.IntegerField(default=0)
    submission_date = models.DateTimeField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    difficulty_level = models.IntegerField(default=2)

    def __str__(self):
        return f"{self.user_id} - {self.task_name}"

    class Meta:
        db_table = 'roadmap_usersubmission'
