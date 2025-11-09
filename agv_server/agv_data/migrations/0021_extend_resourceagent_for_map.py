# Generated migration for ResourceAgent map extension

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('agv_data', '0020_resourceagent_booking'),
    ]

    operations = [
        # Update resource_type field choices and max_length
        migrations.AlterField(
            model_name='resourceagent',
            name='resource_type',
            field=models.CharField(
                choices=[
                    ('CA', 'Crossroad Agent'),
                    ('LSA', 'Logical Segment Agent'),
                    ('DEPOT', 'Depot Station'),
                    ('STATION', 'Pickup/Delivery Station')
                ],
                help_text='Resource type (CA, LSA, DEPOT, or STATION)',
                max_length=10
            ),
        ),
        # Add status field
        migrations.AddField(
            model_name='resourceagent',
            name='status',
            field=models.CharField(
                choices=[
                    ('ONLINE', 'Online'),
                    ('OFFLINE', 'Offline (Maintenance)')
                ],
                default='ONLINE',
                help_text='Resource status (ONLINE or OFFLINE for maintenance)',
                max_length=10
            ),
        ),
        # Add position fields
        migrations.AddField(
            model_name='resourceagent',
            name='pos_x',
            field=models.IntegerField(
                default=0,
                help_text='X coordinate for UI visualization (pixels)'
            ),
        ),
        migrations.AddField(
            model_name='resourceagent',
            name='pos_y',
            field=models.IntegerField(
                default=0,
                help_text='Y coordinate for UI visualization (pixels)'
            ),
        ),
        # Add edge/connection fields
        migrations.AddField(
            model_name='resourceagent',
            name='from_ca',
            field=models.ForeignKey(
                blank=True,
                help_text='(LSA only) Starting node of this edge',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='edges_out',
                to='agv_data.resourceagent'
            ),
        ),
        migrations.AddField(
            model_name='resourceagent',
            name='to_ca',
            field=models.ForeignKey(
                blank=True,
                help_text='(LSA only) Ending node of this edge',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='edges_in',
                to='agv_data.resourceagent'
            ),
        ),
        migrations.AddField(
            model_name='resourceagent',
            name='distance_m',
            field=models.FloatField(
                default=0.0,
                help_text='(LSA only) Distance in meters'
            ),
        ),
        migrations.AddField(
            model_name='resourceagent',
            name='base_time_sec',
            field=models.FloatField(
                default=0.0,
                help_text='(LSA only) Ideal travel time in seconds'
            ),
        ),
    ]
