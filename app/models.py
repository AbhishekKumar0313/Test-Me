from django.db import models

# Create your models here.
class UserDetails(models.Model):
    email = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    
    def __str__(self):
        return self.email
    
class CollectedData(models.Model):
    question=models.TextField()
    answer=models.TextField()
    useranswer=models.TextField(default="")
    question_id = models.IntegerField(unique=True, null=True, blank=True)  
    def save(self, *args, **kwargs):
        if self.question_id is None:  # Only assign if not already set
            last_question = CollectedData.objects.order_by('-question_id').first()
            self.question_id = 1 if not last_question else last_question.question_id + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.question)
    

