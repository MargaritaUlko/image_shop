from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop_app', '0009_artworkembedding'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='quantity',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
