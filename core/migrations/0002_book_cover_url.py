from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='cover_url',
            field=models.URLField(blank=True, default='', help_text='Remote cover image URL'),
        ),
    ]
