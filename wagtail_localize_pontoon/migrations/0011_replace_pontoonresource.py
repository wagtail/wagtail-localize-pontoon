# Generated by Django 2.2.9 on 2019-12-18 18:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("wagtail_localize_translation_memory", "0009_migrate_to_new_location_models"),
        ("wagtailcore", "0041_group_collection_permissions_verbose_name_plural"),
        ("wagtail_localize_pontoon", "0010_remove_page_fields"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="PontoonResource", new_name="OldPontoonResource",
        ),
        migrations.CreateModel(
            name="NewPontoonResource",
            fields=[
                (
                    "object",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="+",
                        serialize=False,
                        to="wagtail_localize_translation_memory.TranslatableObject",
                    ),
                ),
                ("path", models.CharField(max_length=255, unique=True)),
                (
                    "current_revision",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtail_localize_translation_memory.TranslatableRevision",
                    ),
                ),
            ],
        ),
        migrations.RenameField(
            model_name="pontoonresourcesubmission",
            old_name="resource",
            new_name="old_resource",
        ),
        migrations.RenameField(
            model_name="pontoonsynclogresource",
            old_name="resource",
            new_name="old_resource",
        ),
        migrations.AddField(
            model_name="pontoonresourcesubmission",
            name="new_resource",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="submissions",
                to="wagtail_localize_pontoon.NewPontoonResource",
            ),
        ),
        migrations.AddField(
            model_name="pontoonsynclogresource",
            name="new_resource",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="logs",
                to="wagtail_localize_pontoon.NewPontoonResource",
            ),
        ),
    ]