import numpy as np
import tkinter
from scipy.optimize import minimize
from tkinter import *
from tkinter import ttk
import sqlite3

root = Tk()
root.title("BA Calculator")
root.resizable(False, False)

db = sqlite3.connect("BlueArchive.db")
cur = db.cursor()

items_cost = []
final_reward = None


class EventSelection:
    def __init__(self, master):
        my_frame = Frame(master)
        my_frame.pack()
        label = ttk.Label(my_frame, text="Please select an event:")
        label.pack(side=TOP)
        self.selected_event = tkinter.StringVar()
        event_cb = ttk.Combobox(master, textvariable=self.selected_event)

        event_names = cur.execute(
            "SELECT DISTINCT event_name FROM Events "
            "INNER JOIN Missions "
            "ON Events.event_id = Missions.event_ID"
        )
        event_cb["values"] = [
            name[0] for name in event_names
        ]
        event_cb["state"] = "readonly"
        event_cb.pack(side=TOP)

        event_cb.bind("<<ComboboxSelected>>", self.create_form)

    def create_form(self, *args):
        event_name = self.selected_event.get()
        id = cur.execute(
            "SELECT event_id FROM Events "
            "WHERE event_name = '%s'" % event_name
        )
        self.event_id = id.fetchone()[0]
        EventFrame(self.event_id)


class ItemEntry:
    def __init__(self, master, item_ID):
        global items_cost
        my_frame = Frame(master)
        my_frame.pack(side=LEFT)
        self.entries = []
        self.item_cost = []
        item_name = cur.execute(
            "SELECT item_name FROM Items "
            "WHERE item_ID = %i" % item_ID
        )
        item_name = item_name.fetchone()[0]
        store = cur.execute(
            "SELECT Name, Cost, start_qty "
            "FROM Exchange_Store "
            "WHERE item_ID = %i" % item_ID
        )
        Label(my_frame, text=item_name).grid(row=0, column=0, columnspan=2)
        for i, line in enumerate(store):
            Label(my_frame, text=line[0]).grid(row=i + 1, column=0)
            my_entry = Entry(my_frame)
            my_entry.insert(0, line[2])
            my_entry.grid(row=i + 1, column=1)
            self.entries.append(my_entry)
            self.item_cost.append(int(line[1]))
        else:
            Label(my_frame, text="現有").grid(row=i + 2, column=0)
            my_entry = Entry(my_frame)
            my_entry.insert(0, 0)
            my_entry.grid(row=i + 2, column=1)
            self.entries.append(my_entry)
            self.item_cost.append(-1)

    def count(self):
        self.item_qyy = np.array([int(entry.get()) for entry in self.entries])
        self.item_cost = np.array(self.item_cost)
        items_cost.append(sum(self.item_cost * self.item_qyy))


class BonusEntry:

    def __init__(self, master, event_ID):
        my_frame = Frame(master)
        my_frame.pack(side=LEFT)
        self.bonus_entries = []
        self.items_ID = []
        items = cur.execute(
            "SELECT item_ID, item_name "
            "FROM Items "
            "WHERE event_ID = %i "
            "ORDER BY item_ID" % event_ID
        )
        for i, item in enumerate(items):
            Label(my_frame, text=item[1]).grid(row=i, column=0)
            my_entry = Entry(my_frame)
            my_entry.insert("0", "0")
            my_entry.grid(row=i, column=1)
            self.bonus_entries.append(my_entry)
            self.items_ID.append(item[0])

        self.rewards = []
        for item_ID in self.items_ID:
            reward = cur.execute(
                "SELECT reward "
                "FROM Missions "
                "WHERE item_ID = %i "% item_ID
            )
            reward = [item[0] for item in reward]
            self.rewards.append(reward)

    def count(self):
        global final_reward
        self.bonus = np.array([float(entry.get()) for entry in self.bonus_entries])
        self.rewards = np.array(self.rewards)
        final_reward = np.array([(1 + bonus) * reward for bonus, reward in zip(self.bonus, self.rewards)])
        final_reward = np.ceil(final_reward)
        print(final_reward)


class EventFrame:
    def __init__(self, event_id):
        self.result = Toplevel(root)
        self.items_frame = Frame(self.result)
        self.items_frame.pack(side=TOP)
        self.bottom_frame = Frame(self.result)
        self.bottom_frame.pack(side=LEFT)
        self.button_frame = Frame(self.result)
        self.button_frame.pack(side=RIGHT)

        items_id = cur.execute(
            "SELECT item_ID FROM Items "
            "WHERE event_ID = %i" % event_id
        )
        items_id = [i[0] for i in items_id]

        events = [ItemEntry(self.items_frame, item_id)
                  for item_id in items_id]
        missions = cur.execute(
            "SELECT DISTINCT name FROM Missions "
            "WHERE event_ID = %i" % event_id
        )
        self.mission = [mission[0] for mission in missions]

        bonus = BonusEntry(self.bottom_frame, event_id)
        self.result_frame = Frame(self.bottom_frame)
        self.result_frame.pack(side=LEFT)
        my_button = Button(
            self.button_frame, text="Count",
            command=lambda: [
                items_cost.clear(),
                [event.count() for event in events],
                bonus.count(),
                self.count_minimum(items_cost, final_reward)
            ]
        )
        my_button.pack()

    def count_minimum(self, items_cost, final_reward):
        bnds = [(0, 10000) for _ in range(len(self.mission))]
        x0 = np.array([1 for _ in range(len(self.mission))])
        cons = [
            {
                'type': 'ineq',
                'fun': lambda x, coef=i: np.matmul(final_reward[coef], x) - items_cost[coef]
            } for i in range(len(final_reward))
        ]
        sol = minimize(lambda x: sum(x), x0, method="SLSQP", bounds=bnds, constraints=cons)
        for i, name in enumerate(self.mission):
            Label(self.result_frame, text=name).grid(row=i, column=0)
            Label(self.result_frame, text=np.ceil(sol.x[i])).grid(row=i, column=1)


if __name__ == "__main__":
    EventSelection(root)
    root.mainloop()