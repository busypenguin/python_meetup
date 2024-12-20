from django.contrib import admin
from .models import Donate, Lecture, Letters, Program, User, Questions, \
    Letters, Application


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("tg_id", "name", "company", "position", "status")


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
        "start_time",
        "end_time",
        "speaker",
        "status",
    )


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "date")


@admin.register(Donate)
class DonateAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "amount",
        "donated_at",
    )


@admin.register(Questions)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("asker", "answerer", "text", "asked_at")


@admin.register(Letters)
class LetterAdmin(admin.ModelAdmin):
    list_display = ("title", "message", "sent_at")
    readonly_fields = ["sent_at"]


@admin.register(Application)
class ApplitionAdmin(admin.ModelAdmin):
    list_display = ("applicant", "created_at", "accepted")
