# Generated by Django 4.2.13 on 2024-07-09 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kyoapp', '0002_alter_blockendrule_stable_lookback_pattern_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='blockendrule',
            options={'verbose_name': 'Condition End Rule', 'verbose_name_plural': 'Condition End Rules'},
        ),
        migrations.AddField(
            model_name='blockendrule',
            name='name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
