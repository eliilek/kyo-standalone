# Generated by Django 5.0.7 on 2024-08-10 18:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kyoapp', '0006_feedbackmodule_block_feedback_module_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedbackmodule',
            name='name',
            field=models.CharField(default='Potato', max_length=50),
            preserve_default=False,
        ),
    ]
