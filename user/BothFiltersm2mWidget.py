from django import forms


class FilteredSelectMultipleM2M(forms.SelectMultiple):
    """
    A SelectMultiple with a JavaScript filter interface on both side.

    Note that the resulting JavaScript assumes that the jsi18n
    catalog has been loaded in the page
    """
    class Media:
        js = [
            'admin/js/core.js',
            'admin/js/SelectBox.js',
            'user/js/SelectFilterm2m.js',
        ]
        css = {
            'all': ['user/css/SelectFilterm2m.css', ]
        }

    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super().__init__(attrs, choices)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['attrs']['class'] = 'selectfilter'
        if self.is_stacked:
            context['widget']['attrs']['class'] += 'stacked'
        context['widget']['attrs']['data-is-stacked'] = int(self.is_stacked)
        context['widget']['attrs']['data-field-name'] = self.verbose_name
        return context
