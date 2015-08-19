from html import HTML


class Converter(object):

    def __init__(self):
        self.html = HTML()

    #############################
    #    Generator Functions    #
    #############################

    def image(self, path, title):
        '''
        A web-compatible image format (jpg, png, gif, etc.)

        Args:
            path (str): a path to the location on disk where
                        the image is stored.
            title (str): the title of the image.
        '''
        return self.html.img(src=path, alt=title)

    def table(self, table, title, first_row_header=True, first_col_label=True):
        '''
        A table of values.

        Args:
            table ([[], ...]): A 2d list (a list of lists)
                                containing the table data.
                                (row * col)
            title (str): the title of the table
            options(dict): a dictionary of options for this feature
            first_row_header (bool): Whether to use the first row as a header
            first_col_label (bool): Whether to use the first col as labels.
        '''
        div = self.html.div()
        # Create a title.
        div.h3(title, klass='item_title')
        table_tag = div.table()

        # If the first row is a header
        # append header tags to the table tag.
        if first_row_header:
            header = table_tag.tr()
            for x in table[0]:
                header.th(str(x))
            # Remove the header data from the table data.
            table = table[1:]

        for row in table:
            # Make a new row tag.
            row_tag = table_tag.tr()

            # If the first column is a label
            # append a th tag.
            if first_col_label:
                row_tag.th(str(row[0]))
                # Remove the first element.
                row = row[1:]

            for x in row:
                row_tag.td(str(x))

        return div

    def text(self, text, title=None):
        '''
        Some unstructured text.

        Args:
            table ([[], ...]): A 2d list (a list of lists)
                                containing the table data.
                                (row * col)

        '''
        if not title:
            return self.html.p(text)
        else:
            div = self.html.div()
            div.h3(title, klass='item_title')
            div.p(text)
            return div
