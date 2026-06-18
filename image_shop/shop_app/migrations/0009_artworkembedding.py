import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop_app', '0008_order_address_alter_order_status_escrowtransaction_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArtworkEmbedding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vector', models.BinaryField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('artwork', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='embedding',
                    to='shop_app.artwork',
                )),
            ],
        ),
    ]
