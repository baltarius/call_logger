# call_logger.py
"""
Sober application to manually log your calls

Author: elcoyote solitaire
"""
import json
import sqlite3
import tkinter as tk

from datetime import datetime
from tkinter import ttk
from zoneinfo import ZoneInfo

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class CallLogger():
    """
    class for the logging part of the system

    Functions:
        get_db()
        get_timestamp()
        start_call()
        close()
        get_call()
    """
    def __init__(self, db_file="call_logs.db"):
        self.db_file = db_file
        self.conn, self.cur = self.get_db()


    def get_db(self):
        """
        Opens the database, creates the table if it doesn't exists,
        then returns the connection and cursor to be used

        Returns:
             conn as sqlite.connect(db_file)
             cur as sqlite.connection(db_file).cursor()
        """
        db_file = "call_logs.db"
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS calls
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_call TEXT,
            end_call TEXT,
            duration INTEGER,
            in_or_out TEXT,
            company TEXT,
            person TEXT,
            title TEXT,
            transfers TEXT,
            notes TEXT)''')
        conn.commit()
        return conn, cur


    def get_timestamp(self):
        """
        Function to facilitate the timestamp formatting

        Returns:
             timestamp as text for timestamp yyyy/mm/dd HH:MM:SS
        """
        tzone = ZoneInfo("America/Montreal")
        timestamp = datetime.now(tzone).strftime(TIME_FORMAT)
        return timestamp


    def start_call(self, in_or_out):
        """
        Creates a call in the database and returns the last call's id

        Args:
            in_or_out as str for incoming or outgoing direction of the call

        Returns:
             last_id as integer for the last call's id
             timestamp as text for the formatted timestamp
        """
        timestamp = self.get_timestamp()
        self.cur.execute("""
            INSERT INTO calls (
                start_call, in_or_out, company, person, title,
                transfers, end_call, notes, duration
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            in_or_out,
            "",
            "",
            "",
            "[]",
            None,
            "",
            None
        ))
        self.conn.commit()
        return self.cur.lastrowid, timestamp


    def close(self):
        """
        Closes gracefully the database
        when the application shuts down
        """
        self.conn.commit()
        self.conn.close()


    def get_call(self, call_id):
        """
        Fetches a single call from the database

        Args:
            call_id as int for the call ID

        Returns:
            data as dictionary for the call
        """
        self.cur.execute("""
            SELECT *
            FROM calls
            WHERE id=?
        """, (call_id,))
        row = self.cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "start_call": row[1],
            "end_call": row[2],
            "duration": row[3],
            "in_or_out": row[4],
            "company": row[5],
            "person": row[6],
            "title": row[7],
            "transfers": row[8],
            "notes": row[9]
        }


class CallWindow():
    """
    class of the window for the forms

    Functions:
        add_transfer()
        collect_transfers()
        auto_save()
        save()
        end_call()
        save_and_close()
    """
    def __init__(self, master, logger, call_data):
        self.logger = logger
        self.call_id = call_data["id"]
        self.window = tk.Toplevel(master)
        self.window.title(f"Call #{self.call_id}")
        tk.Label(self.window, text=f"Call ID: {self.call_id}").grid(row=0, column=0, columnspan=2)
        tk.Label(self.window, text="Direction").grid(row=1, column=0)
        self.direction_var = tk.StringVar(value=call_data["in_or_out"])
        tk.Entry(self.window, textvariable=self.direction_var).grid(row=1, column=1)
        tk.Label(self.window, text="Start Time").grid(row=2, column=0)
        self.start_var = tk.StringVar(value=call_data["timestamp"])
        tk.Entry(self.window, textvariable=self.start_var).grid(row=2, column=1)
        tk.Label(self.window, text="Company").grid(row=3, column=0)
        self.company_var = tk.StringVar(value=call_data["company"])
        tk.Entry(self.window, textvariable=self.company_var).grid(row=3, column=1)
        tk.Label(self.window, text="Person").grid(row=4, column=0)
        self.person_var = tk.StringVar(value=call_data["person"])
        tk.Entry(self.window, textvariable=self.person_var).grid(row=4, column=1)
        tk.Label(self.window, text="Title").grid(row=5, column=0)
        self.title_var = tk.StringVar(value=call_data["title"])
        tk.Entry(self.window, textvariable=self.title_var).grid(row=5, column=1)
        tk.Label(self.window, text="End Time").grid(row=6, column=0)
        self.end_var = tk.StringVar(value=call_data["end_call"])
        tk.Entry(self.window, textvariable=self.end_var).grid(row=6, column=1)
        tk.Label(self.window, text="Transfers").grid(row=7, column=0, columnspan=2)
        self.transfer_frame = tk.Frame(self.window)
        self.transfer_frame.grid(row=8, column=0, columnspan=2)
        self.transfers = []
        saved_transfers = json.loads(call_data["transfers"])
        for transfer in saved_transfers:
            self.add_transfer(
                transfer["time"],
                transfer["name"],
                transfer["title"]
            )
        tk.Button(self.window, text="Add Transfer",
                  command=self.add_transfer).grid(row=9, column=0, columnspan=2)
        tk.Label(self.window, text="Notes").grid(row=10, column=0, columnspan=2)
        self.notes_text = tk.Text(self.window, height=5, width=40)
        self.notes_text.grid(row=11, column=0, columnspan=2)
        self.notes_text.insert("1.0", call_data["notes"])
        tk.Button(self.window, text="Save", command=self.save).grid(row=12, column=0)
        self.end_button = tk.Button(self.window, text="End call", command=self.end_call)
        self.end_button.grid(row=12, column=1)
        self.end_button.config(state="disabled" if self.end_var.get() else "normal")
        tk.Button(self.window, text="Save & Close", command=self.save_close).grid(row=12, column=2)
        self.window.after(60000, self.auto_save)


    def add_transfer(self, time_value=None, name_value="", title_value=""):
        """
        Creates new line for a call transfer

        Args:
            time_value as str for the timestamp of the transfer
            name_value as str for the name of the person
            title_value as str for the title of the person
        """
        row = len(self.transfers)
        time_var = tk.StringVar(
            value=time_value or self.logger.get_timestamp()
        )
        name_var = tk.StringVar(value=name_value)
        title_var = tk.StringVar(value=title_value)
        tk.Entry(self.transfer_frame, textvariable=time_var, width=18).grid(row=row, column=0)
        tk.Entry(self.transfer_frame, textvariable=name_var, width=15).grid(row=row, column=1)
        tk.Entry(self.transfer_frame, textvariable=title_var, width=15).grid(row=row, column=2)
        self.transfers.append((time_var, name_var, title_var))


    def collect_transfers(self):
        """
        Fetches all current transfers from the call

        Returns:
            data as dictionary for the transfers in the call
        """
        data = []
        for timez, name, title in self.transfers:
            data.append({
                "time": timez.get(),
                "name": name.get(),
                "title": title.get()
            })
        return data


    def auto_save(self):
        """
        Saves automatically every 60 seconds
        """
        self.save()
        self.window.after(60000, self.auto_save)


    def save(self):
        """
        Function to save the data in the database
        """
        transfers_json = json.dumps(self.collect_transfers())
        duration = None
        if self.end_var.get():
            start = datetime.strptime(self.start_var.get(), TIME_FORMAT)
            end = datetime.strptime(self.end_var.get(), TIME_FORMAT)
            duration = int((end - start).total_seconds())
        self.logger.cur.execute("""
            UPDATE calls SET
                start_call=?,
                end_call=?,
                duration=?,
                in_or_out=?,
                company=?,
                person=?,
                title=?,
                transfers=?,
                notes=?
            WHERE id=?
        """, (
            self.start_var.get(),
            self.end_var.get(),
            duration,
            self.direction_var.get(),
            self.company_var.get(),
            self.person_var.get(),
            self.title_var.get(),
            transfers_json,
            self.notes_text.get("1.0", tk.END),
            self.call_id
        ))
        self.logger.conn.commit()


    def end_call(self):
        """
        Adds the timestamp in the End Time
        part of the call logger then saves
        """
        if not self.end_var.get():
            timestamp = self.logger.get_timestamp()
            self.end_var.set(timestamp)
        self.save()


    def save_close(self):
        """
        Function to save the data
        in the database then exit
        """
        self.save()
        self.window.destroy()



class App():
    """
    main class for the application

    Functions:
        new_call()
        open_viewer()
        on_close()
    """
    def __init__(self, master):
        self.root = master
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.title("Call Logger")
        self.logger = CallLogger()
        tk.Button(master, text="Incoming Call", width=25,
                  command=lambda: self.new_call("incoming")).pack(pady=10)
        tk.Button(master, text="Outgoing Call", width=25,
                  command=lambda: self.new_call("outgoing")).pack(pady=10)
        tk.Button(master, text="View Calls", width=25,
                  command=self.open_viewer).pack(pady=10)


    def new_call(self, direction):
        """
        Opens a form for a new call

        Args:
            direction as str for the incoming or outgoing direction of the call
        """
        call_id, timestamp = self.logger.start_call(direction)
        call_data = {
            "id": call_id,
            "start_call": timestamp,
            "end_call": "",
            "duration": "",
            "in_or_out": direction,
            "company": "",
            "person": "",
            "title": "",
            "transfers": "[]",
            "notes": ""
        }
        CallWindow(self.root, self.logger, call_data)


    def open_viewer(self):
        """
        Opens the viewer's window to display the calls
        """
        CallsViewer(self.root, self.logger)


    def on_close(self):
        """
        Closes gracefully the application
        after saving the data in the database
        """
        self.logger.close()
        self.root.destroy()



class CallsViewer:
    """
    class for the calls viewer window

    Functions:
        load_data()
        sort_by()
        open_call()
    """
    def __init__(self, master, logger):
        self.logger = logger
        self.window = tk.Toplevel(master)
        self.window.title("Call History")
        columns = (
            "id", "start", "end", "duration",
            "direction", "company", "person", "title"
        )
        self.tree = ttk.Treeview(self.window, columns=columns, show="headings")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_call)
        for col in columns:
            self.tree.heading(col, text=col.title(),
                              command=lambda c=col: self.sort_by(c, False))
            self.tree.column(col, width=100)
        self.load_data()
        tk.Button(self.window, text="Refresh", command=self.load_data).pack()


    def load_data(self):
        """
        Fetches the data from the database
        then displays it in the viewer
        """
        self.tree.delete(*self.tree.get_children())
        self.logger.cur.execute("SELECT * FROM calls")
        rows = self.logger.cur.fetchall()
        for row in rows:
            self.tree.insert("", "end", values=(
                row[0],  # id
                row[1],  # start
                row[2],  # end
                row[3],  # duration
                row[4],  # direction
                row[5],  # company
                row[6],  # person
                row[7],  # title
            ))


    def sort_by(self, col, reverse):
        """
        Allows to sort the calls by column

        Args:
            col as str for the column name to sort
            reverse as bool for reversing or not the order
        """
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            data.sort(key=lambda t: float(t[0]) if t[0] else 0, reverse=reverse)
        except ValueError:
            data.sort(key=lambda t: t[0], reverse=reverse)
        for index, (_, k) in enumerate(data):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_by(col, not reverse))


    def open_call(self, _event):
        """
        Opens the selected call in a CallWindow
        """
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        call_id = item["values"][0]
        call_data = self.logger.get_call(call_id)
        if call_data:
            CallWindow(
                self.window,
                self.logger,
                call_data
            )



if __name__ == "__main__":
    main_window = tk.Tk()
    app = App(main_window)
    main_window.mainloop()
