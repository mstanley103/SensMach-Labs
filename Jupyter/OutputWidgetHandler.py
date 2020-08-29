# Output handler for use with standard python logging library.
# This code was adopted from the following source with only minor modification:
# https://ipywidgets.readthedocs.io/en/latest/examples/Output%20Widget.html

import ipywidgets as widgets
import logging

class OutputWidgetHandler(logging.Handler):
    """ Custom logging handler sending logs to an output widget """

    def __init__(self, *args, **kwargs):
        super(OutputWidgetHandler, self).__init__(*args, **kwargs)
        layout = {
            'width': '100%',
            'height': '200px',
            'border': '1px solid black',
            'overflow': 'scroll'
        }
        self.out = widgets.Output(layout=layout)

    def emit(self, record):
        """ Overload of logging.Handler method """
        formatted_record = self.format(record)
        new_output = {
            'name': 'stdout',
            'output_type': 'stream',
            'text': formatted_record+'\n'
        }
        self.out.outputs = self.out.outputs + (new_output, )

    def show_logs(self):
        """ Show the logs """
        display(self.out)

    def clear(self):
        """ Clear the current logs """
        self.out.clear_output()


