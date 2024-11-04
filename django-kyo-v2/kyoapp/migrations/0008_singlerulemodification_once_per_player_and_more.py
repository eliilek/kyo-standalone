# Generated by Django 5.0.7 on 2024-08-22 22:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kyoapp', '0007_feedbackmodule_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='singlerulemodification',
            name='once_per_player',
            field=models.BooleanField(default=False, verbose_name='Can only apply once per player'),
        ),
        migrations.CreateModel(
            name='SingleRuleModificationInstance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seat_number', models.PositiveSmallIntegerField()),
                ('modification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kyoapp.singlerulemodification')),
                ('rule_instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kyoapp.ruleinstance')),
            ],
        ),
    ]
