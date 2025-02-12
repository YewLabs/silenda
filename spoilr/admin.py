from django.contrib import admin
from django.shortcuts import redirect, reverse
from django.db.models import Q, Count
from .models import *

def noInfinite(qs):
    return (qs.exclude(round__url='infinite') | qs.filter(round__url='infinite', is_meta=True)).order_by('name').select_related('round')


class InteractionAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['puzzle'].queryset = noInfinite(Puzzle.objects)
        return super(InteractionAdmin, self).render_change_form(request, context, *args, **kwargs)
    def get_queryset(self, request):
        return (super(InteractionAdmin, self)
            .get_queryset(request)
            .annotate(count_teams_pending=Count('interactionaccess', filter=Q(interactionaccess__accomplished=False), distinct=True))
            .annotate(count_teams_accomplished=Count('interactionaccess', filter=Q(interactionaccess__accomplished=True), distinct=True)))
    def teams_pending(interaction):
        return interaction.count_teams_pending
    teams_pending.short_description = 'Teams Pending'
    def teams_accomplished(interaction):
        return interaction.count_teams_accomplished
    teams_accomplished.short_description = 'Teams Accomplished'
    list_display = ('__str__', teams_pending, teams_accomplished)
    search_fields = ['url', 'name']
    ordering = ['order']

class RoundPuzzleInline(admin.TabularInline):
    model = Puzzle
    extra = 0
    ordering = ['order']

class RoundAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(RoundAdmin, self)
            .get_queryset(request)
            .annotate(count_teams_open=Count('roundaccess', distinct=True))
            .annotate(count_puzzles=Count('puzzle', distinct=True)))
    def teams_open(round):
        return round.count_teams_open
    teams_open.short_description = 'Teams Open'
    def puzzles(round):
        return round.count_puzzles
    puzzles.short_description = 'Puzzles'
    list_display = ('__str__', puzzles, teams_open)
    search_fields = ['url', 'name']
    ordering = ['order']
    def get_inlines(self, request, obj):
        if obj and obj.url == 'infinite': return []
        return [RoundPuzzleInline]

from django.contrib.admin import SimpleListFilter

class NoInfiniteFilter(SimpleListFilter):
    title = ''

    parameter_name = ''

    def lookups(self, request, model_admin):
        return (
            ('all', 'All'),
        )

    def queryset(self, request, queryset):
        return queryset.exclude(round__url='infinite')

class PuzzleAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(PuzzleAdmin, self)
            .get_queryset(request)
            .annotate(count_teams_open=Count('puzzleaccess', distinct=True))
            .annotate(count_teams_solved=Count('puzzleaccess', filter=Q(puzzleaccess__solved=True), distinct=True)))
    def teams_open(puzzle):
        return puzzle.count_teams_open
    teams_open.short_description = 'Teams Open'
    def teams_solved(puzzle):
        return puzzle.count_teams_solved
    teams_solved.short_description = 'Teams Solved'
    list_display = ('__str__', 'name', 'round', teams_open, teams_solved)
    list_filter = [NoInfiniteFilter, 'round__name']
    search_fields = ['url', 'name']
    ordering = ['order']

class PseudoAnswerAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(PseudoAnswerAdmin, self)
            .get_queryset(request)
            .select_related('puzzle'))
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['puzzle'].queryset = noInfinite(Puzzle.objects)
        return super(PseudoAnswerAdmin, self).render_change_form(request, context, *args, **kwargs)


class PuzzleExtraDataAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['puzzle'].queryset = noInfinite(Puzzle.objects)
        return super(PuzzleExtraDataAdmin, self).render_change_form(request, context, *args, **kwargs)

    list_display = ('puzzle', 'name', 'data')
    list_filter = ['puzzle__round__name', 'name']
    search_fields = ['puzzle__url', 'puzzle__name', 'name', 'data']

admin.site.register(Interaction, InteractionAdmin)
admin.site.register(Round, RoundAdmin)
admin.site.register(Puzzle, PuzzleAdmin)
admin.site.register(PseudoAnswer, PseudoAnswerAdmin)
admin.site.register(PuzzleExtraData, PuzzleExtraDataAdmin)

class TeamExtraDataAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(TeamExtraDataAdmin, self)
            .get_queryset(request)
            .select_related('team'))
    def team_name(data):
        return data.team.name
    list_display = (team_name, 'name', 'data')
    list_filter = ['name', 'team__name']
    search_fields = [team_name, 'name', 'data']

admin.site.register(TeamExtraData, TeamExtraDataAdmin)

class TeamRoundInline(admin.TabularInline):
    model = Team.rounds.through
    extra = 0
    ordering = ['round__order']
    readonly_fields = ('round', 'timestamp')
    def get_queryset(self, request):
        return (super(TeamRoundInline, self)
            .get_queryset(request)
            .select_related('team', 'round'))

class TeamPuzzleInline(admin.TabularInline):
    model = Team.puzzles.through
    extra = 0
    ordering = ['puzzle__round__order', 'puzzle__order']
    readonly_fields = ('puzzle', 'timestamp', 'found_timestamp', 'solved_time')
    def get_queryset(self, request):
        return (super(TeamPuzzleInline, self)
            .get_queryset(request)
            .select_related('team', 'puzzle', 'puzzle__round')
            .exclude(puzzle__round__url='infinite'))

class TeamAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(TeamAdmin, self)
            .get_queryset(request)
            .annotate(count_rounds_open=Count('roundaccess', distinct=True))
            .annotate(count_metapuzzles_solved=Count('puzzleaccess', filter=Q(puzzleaccess__solved=True, puzzleaccess__puzzle__is_meta=True), distinct=True))
            .annotate(count_puzzles_open=Count('puzzleaccess', distinct=True))
            .annotate(count_puzzles_solved=Count('puzzleaccess', filter=Q(puzzleaccess__solved=True), distinct=True))
            .annotate(count_puzzles_unsolved=Count('puzzleaccess', filter=Q(puzzleaccess__solved=False), distinct=True)))
    def rounds_open(team):
        return team.count_rounds_open
    rounds_open.short_description = 'Rounds Open'
    def metapuzzles_solved(team):
        return team.count_metapuzzles_solved
    metapuzzles_solved.short_description = 'Metapuzzles Solved'
    def puzzles_open(team):
        return team.count_puzzles_open
    puzzles_open.short_description = 'Puzzles Open'
    def puzzles_solved(team):
        return team.count_puzzles_solved
    puzzles_solved.short_description = 'Puzzles Solved'
    def puzzles_unsolved(team):
        return team.count_puzzles_unsolved
    puzzles_unsolved.short_description = 'Puzzles Unsolved'
    inlines = [TeamRoundInline, TeamPuzzleInline]
    list_display = ('__str__', 'username', rounds_open, metapuzzles_solved, puzzles_open, puzzles_solved, puzzles_unsolved)
    search_fields = ['name', 'username']

admin.site.register(Team, TeamAdmin)

class LogTeamFilter(admin.SimpleListFilter):
    title = 'team'
    parameter_name = 'team'
    def lookups(self, request, model_admin):
        return [(x.name, x.name) for x in Team.objects.all()]
    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(team__name=self.value())

class SystemLogAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(SystemLogAdmin, self)
            .get_queryset(request)
            .select_related('team'))
    def team_name(data):
        if data.team:
            return data.team.name
        else:
            return ''
    list_display = ('timestamp', 'event_type', team_name, 'object_id', 'message')
    list_filter = ('event_type', LogTeamFilter, 'object_id')
    search_fields = [team_name, 'event_type', 'object_id', 'message']

admin.site.register(SystemLog, SystemLogAdmin)

class TeamLogAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(TeamLogAdmin, self)
            .get_queryset(request)
            .select_related('team'))
    def team_name(data):
        return data.team.name
    list_display = ('timestamp', team_name, 'event_type', 'object_id', 'message')
    list_filter = (LogTeamFilter, 'event_type', 'object_id')
    search_fields = [team_name, 'event_type', 'object_id', 'message']

admin.site.register(TeamLog, TeamLogAdmin)

class RoundAccessRoundFilter(admin.SimpleListFilter):
    title = 'round'
    parameter_name = 'round'
    def lookups(self, request, model_admin):
        return [(x.name, x.name) for x in Round.objects.all()]
    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(round__name=self.value())

class RoundAccessAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'team', 'round')
    list_filter = (RoundAccessRoundFilter, 'team__name')
    search_fields = ['team__name', 'round__name']
    ordering = ['team__name', 'round__order']

class PuzzleAccessRoundFilter(admin.SimpleListFilter):
    title = 'round'
    parameter_name = 'round'
    def lookups(self, request, model_admin):
        return [(x.name, x.name) for x in Round.objects.all()]
    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(puzzle__round__name=self.value())

def mark_found(modeladmin, request, queryset):
    queryset.update(found=True)
def mark_unfound(modeladmin, request, queryset):
    queryset.update(found=False)
def mark_solved(modeladmin, request, queryset):
    queryset.update(solved=True)
def mark_unsolved(modeladmin, request, queryset):
    queryset.update(solved=False)

class PuzzleAccessAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['puzzle'].queryset = noInfinite(Puzzle.objects)
        return super(PuzzleAccessAdmin, self).render_change_form(request, context, *args, **kwargs)

    list_display = ('__str__', 'team', 'puzzle', 'found', 'solved')
    list_filter = (PuzzleAccessRoundFilter, 'found', 'solved', 'team__name')
    search_fields = ['team__name', 'puzzle__name', 'puzzle__round__name']
    ordering = ['team__name', 'puzzle__round__order', 'puzzle__order']
    actions = [mark_found, mark_unfound, mark_solved, mark_unsolved]

class InteractionAccessAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'team', 'interaction', 'accomplished')
    list_filter = ('interaction', 'accomplished', 'team__name')
    search_fields = ['team__name', 'interaction__name']
    ordering = ['team__name', 'interaction__order']

admin.site.register(RoundAccess,RoundAccessAdmin)
admin.site.register(PuzzleAccess,PuzzleAccessAdmin)
admin.site.register(InteractionAccess,InteractionAccessAdmin)

class HintSubmissionAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['puzzle'].queryset = noInfinite(Puzzle.objects)
        return super(HintSubmissionAdmin, self).render_change_form(request, context, *args, **kwargs)

    list_display = ('__str__', 'timestamp', 'team', 'puzzle', 'resolved')
    list_filter = (PuzzleAccessRoundFilter, 'resolved', 'team__name')
    search_fields = ['team__name', 'puzzle__name', 'puzzle__round__name']
    ordering = ['timestamp']

admin.site.register(HintSubmission, HintSubmissionAdmin)

class PuzzleSubmissionAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['puzzle'].queryset = noInfinite(Puzzle.objects)
        return super(PuzzleSubmissionAdmin, self).render_change_form(request, context, *args, **kwargs)

    list_display = ('__str__', 'timestamp', 'team', 'puzzle', 'resolved')
    list_filter = (PuzzleAccessRoundFilter, 'resolved', 'team__name')
    search_fields = ['team__name', 'puzzle__name', 'puzzle__round__name']
    ordering = ['timestamp']

admin.site.register(PuzzleSubmission,PuzzleSubmissionAdmin)

class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'timestamp', 'team', 'contact', 'comment', 'resolved')
    list_filter = ('resolved', 'team__name')
    search_fields = ['team__name', 'comment']
    ordering = ['timestamp']

admin.site.register(ContactRequest,ContactRequestAdmin)

class QueueHandlerAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(QueueHandlerAdmin, self)
            .get_queryset(request)
            .select_related('team', 'contact_team'))
    list_display = ('__str__', 'email')
    list_filter = ('name', 'team__name')
    search_fields = ['name', 'email', 'team__name']

admin.site.register(QueueHandler,QueueHandlerAdmin)

class PuzzleSurveyAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return (super(PuzzleSurveyAdmin, self)
            .get_queryset(request)
            .select_related('team', 'puzzle'))
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['puzzle'].queryset = noInfinite(Puzzle.objects)
        return super(PuzzleSurveyAdmin, self).render_change_form(request, context, *args, **kwargs)

    list_display = ('__str__', 'fun', 'difficulty', 'timestamp')
    list_filter = (PuzzleAccessRoundFilter, 'fun', 'difficulty', 'team__name')
    search_fields = ['team__name', 'puzzle__name', 'puzzle__round__name', 'comment']

admin.site.register(PuzzleSurvey,PuzzleSurveyAdmin)

class HQUpdateAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['puzzle'].queryset = noInfinite(Puzzle.objects)
        return super(HQUpdateAdmin, self).render_change_form(request, context, *args, **kwargs)

    def response_add(sefl, request, obj, post_url_continue=None):
        return redirect(reverse('hq_updates'))

    readonly_fields = ('published', 'creation_time', 'modification_time', 'publish_time')
    list_display = ('__str__', 'team', 'puzzle', 'send_email')

admin.site.register(HQUpdate, HQUpdateAdmin)

admin.site.register(IncomingMessage)
admin.site.register(OutgoingMessage)
