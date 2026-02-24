# coding: utf-8
# Imports généraux
import os, sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.scrolledtext as scrolledtext
import csv 
import tkinter.scrolledtext as scrolledtext
from collections import defaultdict, OrderedDict
# Imports spécifiques
from crue10.utils.configuration import Configuration
from crue10.utils.design_patterns import factory_define
from crue10.utils.otf import OTF
from crue10.etude import Etude


"""
Interface graphique de l'outil otf developpé par PBA.
Version provisoire - utilisée dans les recette de GéoRelai
"""

@factory_define('guiOTF')               
class guiOTF():
    """ Interface utilisateur pour l'outil de test.
    """
    # Constante de classe: configuration par défaut pour OTF
    DIC_CFG_DFT = {
        'nom_etu_a': None,
        'nom_sce_a': None,
        'nom_smo_a': None,
        'nom_etu_b': None,
        'nom_sce_b': None,
        'nom_smo_b': None
    }

    def __init__(self) -> None:
        """ Construire l'instance de classe.
        """

        # Initialiser les objets utitaires
        self.cfg = Configuration(               # Dictionnaire de configuration métier
            lst_cfg=[guiOTF.DIC_CFG_DFT, 'user.json'], fic_sav='user.json')
        self.oft = OTF()                        # Objet de comparaison

    def select_input(self) -> None:
        """ Sélectionner les données d'entrée dans une fenêtre dédiée.
        Met à jour les variables membres concernant la première et la seconde étude.
        """
        # Construire l'IHM de selection des études / Scénario / Sous-modèle 
        root = tk.Tk()
        root.title("Sélection ETU → Scénario → Sous‑modèle")
        frm = ttk.Frame(root, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")

        # Lecture de l'ETU A
        ttk.Label(frm, text="ETU A :").grid(row=0, column=0, sticky="w")
        entry_a = ttk.Entry(frm, width=70)
        if self.cfg['nom_etu_a'] is not None :  # Pour éviter les None si le fichier config absent.
            entry_a.insert(0, self.cfg['nom_etu_a']) 
        entry_a.grid(row=0, column=1, sticky="w")
        combo_scen_a = ttk.Combobox(frm, values=[self.cfg['nom_sce_a'],None], state='readonly', width=50)
        combo_scen_a.current(0)
        combo_sous_a = ttk.Combobox(frm, values=[self.cfg['nom_smo_a'],None], state='readonly', width=50)
        combo_sous_a.current(0)
        btn_a = ttk.Button(frm, text="Choisir...", command=lambda: self.choix_file_and_maj(entry_a, combo_scen_a, combo_sous_a, "Choisir ETU A", self.cfg['nom_etu_a']))
        btn_a.grid(row=0, column=2, padx=5)

        ttk.Label(frm, text="Scénario A :").grid(row=1, column=0, sticky="w")
        combo_scen_a.grid(row=1, column=1, sticky="w")
        combo_scen_a.bind("<<ComboboxSelected>>", lambda e: self.fill_sousmodeles(combo_scen_a, combo_sous_a))
        ttk.Label(frm, text="Sous-modèle A :").grid(row=2, column=0, sticky="w")
        combo_sous_a.grid(row=2, column=1, sticky="w")
        ttk.Separator(frm, orient='horizontal').grid(row=3, column=0, columnspan=3, sticky='ew', pady=8)

        # Selection de l'ETU B
        ttk.Label(frm, text="ETU B :").grid(row=4, column=0, sticky="w")
        entry_b = ttk.Entry(frm, width=70)
        if self.cfg['nom_etu_a'] is not None : 
            entry_b.insert(0, self.cfg['nom_etu_b']) 
        entry_b.grid(row=4, column=1, sticky="w")
        combo_scen_b = ttk.Combobox(frm, values=[self.cfg['nom_sce_b'], None], state='readonly', width=50)
        combo_scen_b.current(0)
        combo_sous_b = ttk.Combobox(frm, values=[self.cfg['nom_smo_b'], None], state='readonly', width=50)
        combo_sous_b.current(0)
        btn_b = ttk.Button(frm, text="Choisir...", command=lambda: self.choix_file_and_maj(entry_b, combo_scen_b, combo_sous_b, "Choisir ETU B"))
        btn_b.grid(row=4, column=2, padx=5)
        ttk.Label(frm, text="Scénario B :").grid(row=5, column=0, sticky="w")
        combo_scen_b.grid(row=5, column=1, sticky="w")
        combo_scen_b.bind("<<ComboboxSelected>>", lambda e: self.fill_sousmodeles(combo_scen_b, combo_sous_b))
        ttk.Label(frm, text="Sous-modèle B :").grid(row=6, column=0, sticky="w")
        combo_sous_b.grid(row=6, column=1, sticky="w")

        # Bouton Valider / Annuler : vérification de saisi des champs 
        def validate():
            self.cfg['nom_etu_a'] = entry_a.get().strip()
            self.cfg['nom_etu_b'] = entry_b.get().strip()
            self.cfg['nom_sce_a'] = combo_scen_a.get().strip()
            self.cfg['nom_sce_b'] = combo_scen_b.get().strip()
            self.cfg['nom_smo_a'] = combo_sous_a.get().strip()
            self.cfg['nom_smo_b'] = combo_sous_b.get().strip()
            if not self.cfg['nom_etu_a'] or not self.cfg['nom_etu_b']:
                messagebox.showwarning("Champs manquants", "Veuillez sélectionner les deux fichiers ETU.")
                return
            self.cfg.save()
            root.quit()

        def cancel():
            root.quit()

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Valider", command=validate).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Annuler", command=cancel).grid(row=0, column=1, padx=5)

        # Layout expand
        root.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

        root.mainloop()
        root.destroy()

    ## Lecture du fichier *.etu.xml et scan des scénarios et Sous-modèle existants
    def choix_file_and_maj(self, entry, combo_scenarios, combo_sousmodeles, title="Choisir ETU XML", ini_path: str = None):
        """ Lire un fichier d'étude et mettre à jour les champs Scénario et Sous-modèle dans l'IHM
            """
        ini_dir, ini_fic = os.path.split(ini_path) if ini_path is not None else None, None
        #Selection du fichier etu.xml
        path = filedialog.askopenfilename(
            title=title,
            filetypes=(("Fichier Etude", "*.etu.xml"),),
            initialdir=ini_dir,
            initialfile=ini_fic
        )
        if not path:
            return
        entry.delete(0, tk.END)
        entry.insert(0, path)

        # Instancier Etude sans lecture 
        try:
            etudebox = Etude(path)
        except NameError:
            messagebox.showerror("Erreur", "La classe `Etude` n'est pas définie dans l'environnement.")
            combo_scenarios['values'] = []
            combo_scenarios.set('')
            combo_sousmodeles['values'] = []
            combo_sousmodeles.set('')
            return
        except Exception as e:
            messagebox.showerror("Erreur Etude", f"Impossible d'ouvrir/lire l'étude :\n{e}")
            combo_scenarios['values'] = []
            combo_scenarios.set('')
            combo_sousmodeles['values'] = []
            combo_sousmodeles.set('')
            return

        # Récupération des scénarios depuis l'objet Etude
        try:
            scenarios = [sce.id for sce in etudebox.get_liste_scenarios()]
        except Exception as e:
            messagebox.showerror("Erreur scénarios", f"Impossible d'obtenir la liste des scénarios :\n{e}")
            combo_scenarios['values'] = []
            combo_scenarios.set('')
            combo_sousmodeles['values'] = []
            combo_sousmodeles.set('')
            return
        scenarios_list = scenarios
        combo_scenarios['values'] = scenarios_list
        combo_scenarios.set(scenarios_list[0] if scenarios_list else '')
        # Attacher l'objet Etude au combobox pour réutilisation
        combo_scenarios._etudebox = etudebox
        # Initialiser les sous-modèles pour le scénario sélectionné (s'il y en a)
        if scenarios_list:
            # appel sans passer etudebox
            self.fill_sousmodeles(combo_scenarios, combo_sousmodeles)

    def fill_sousmodeles(self,combo_scenarios, combo_sousmodeles):
        """
        Récuperer et mettre à jour le champ `combo_sousmodeles` dans l'IHM.
        """
        # affichée dans la combobox (ex: "Scénario Sc_multi_sm_...")  # l'ideale le Sc_...:
        scenario_display = combo_scenarios.get().strip()
        if not scenario_display:
            combo_sousmodeles['values'] = []
            combo_sousmodeles.set('')
            return

        # Retrouver l'objet Etude stocké sur le combobox
        etudebox = getattr(combo_scenarios, '_etudebox', None)
        if etudebox is None:
            messagebox.showerror("Erreur", "Objet Etude introuvable — sélectionnez d'abord le fichier ETU.")
            combo_sousmodeles['values'] = []
            combo_sousmodeles.set('')
            return
        scenario_key = scenario_display

        try:
            #Recuperer l'objet scenario via Etude
            scenario_obj = etudebox.get_scenario(scenario_key)
            #Accéder au modèle et à la liste des sous-modeles
            modele =scenario_obj.modele
    
            if modele is None:
                raise RuntimeError("Le scénario n'a pas d'attribut 'modele'.")
            
            sous_list = [smo.id for smo in modele.liste_sous_modeles]

        except Exception as e:
            messagebox.showerror("Erreur sous-modèles", f"Impossible d'obtenir la liste des sous-modèles :\n{e}")
            combo_sousmodeles['values'] = []
            combo_sousmodeles.set('')
            return
        combo_sousmodeles['values'] = sous_list
        combo_sousmodeles.set(sous_list[0] if sous_list else '')

    def afficher_differences(self):
        """
        Fenêtre d'affichage des différences, avec groupes parent/enfants et carets +/- par ligne
        (utilise la colonne arbre '#0' pour afficher le chemin).
        """
        otf = OTF()
        dic_diff = otf.diff_crue10(nom_etu_a=gui.cfg["nom_etu_a"], nom_sce_a=gui.cfg["nom_sce_a"], nom_smo_a=gui.cfg["nom_smo_a"],
            nom_etu_b=gui.cfg["nom_etu_b"], nom_sce_b=gui.cfg["nom_sce_b"], nom_smo_b=gui.cfg["nom_smo_b"])
        win = tk.Tk()
        win.title("Differences - affichage détaillé")

        # Top frame : filtres et actions
        topfrm = ttk.Frame(win, padding=6)
        topfrm.grid(row=0, column=0, sticky="ew")

        ttk.Label(topfrm, text="Filtre sévérité:").grid(row=0, column=0, sticky="w")
        combo_sev = ttk.Combobox(topfrm, values=["Toutes", "0 - Anodine", "1 - Mineure", "2 - Majeure"], state='readonly', width=18)
        combo_sev.current(0)
        combo_sev.grid(row=0, column=1, padx=6)

        ttk.Label(topfrm, text="Rechercher:").grid(row=0, column=2, sticky="w")
        entry_search = ttk.Entry(topfrm, width=30)
        entry_search.grid(row=0, column=3, padx=6)

        var_show_a = tk.BooleanVar(value=True)
        var_show_b = tk.BooleanVar(value=True)
        ttk.Checkbutton(topfrm, text="Afficher A", variable=var_show_a).grid(row=0, column=4, padx=6)
        ttk.Checkbutton(topfrm, text="Afficher B", variable=var_show_b).grid(row=0, column=5, padx=6)

        # Expand/collapse buttons (globaux) + actions
        btn_expand_all = ttk.Button(topfrm, text="Tout développer", command=lambda: expand_all())
        btn_expand_all.grid(row=0, column=6, padx=4)
        btn_collapse_all = ttk.Button(topfrm, text="Tout réduire", command=lambda: collapse_all())
        btn_collapse_all.grid(row=0, column=7, padx=4)
        btn_toggle_sel = ttk.Button(topfrm, text="Basculer sélection", command=lambda: toggle_selected())
        btn_toggle_sel.grid(row=0, column=8, padx=4)

        btn_search = ttk.Button(topfrm, text="Filtrer", command=lambda: refresh_view())
        btn_search.grid(row=0, column=9, padx=6)
        btn_clear = ttk.Button(topfrm, text="Réinitialiser", command=lambda: (combo_sev.current(0), entry_search.delete(0, tk.END), var_show_a.set(True), var_show_b.set(True), refresh_view()))
        btn_clear.grid(row=0, column=10, padx=6)
        btn_export = ttk.Button(topfrm, text="Exporter...", command=lambda: export_diff())
        btn_export.grid(row=0, column=11, padx=6)
        btn_copy = ttk.Button(topfrm, text="Copier sélection", command=lambda: copy_selection())
        btn_copy.grid(row=0, column=12, padx=6)

        # Treeview : utiliser la colonne #0 pour le chemin afin d'afficher caret +/- par ligne
        cols = ('sev', 'a', 'b')
        tree = ttk.Treeview(win, columns=cols, show='tree headings', height=20)
        tree.heading('#0', text='Niveau / Chemin')
        tree.heading('sev', text='Sévérité')
        tree.heading('a', text='Valeur A')
        tree.heading('b', text='Valeur B')
        tree.column('#0', width=600, anchor='w')
        tree.column('sev', width=90, anchor='center')
        tree.column('a', width=260, anchor='w')
        tree.column('b', width=260, anchor='w')
        tree.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        # Scrollbar vertical
        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        vsb.grid(row=1, column=1, sticky='ns')
        tree.configure(yscrollcommand=vsb.set)

        # Tags couleurs par sévérité
        tree.tag_configure('sev0', foreground='gray20', background='#f2f2f2')
        tree.tag_configure('sev1', foreground='black', background='#fff2cc')
        tree.tag_configure('sev2', foreground='black', background='#ffd6d6')

        status = ttk.Label(win, text="")
        status.grid(row=2, column=0, sticky='ew', padx=6)

        # Panneau détail en bas
        detail_label = ttk.Label(win, text="Détail (sélection):")
        detail_label.grid(row=3, column=0, sticky='w', padx=6)
        detail_text = scrolledtext.ScrolledText(win, height=10, wrap='word')
        detail_text.grid(row=4, column=0, columnspan=2, sticky='nsew', padx=6, pady=(0,6))
        detail_text.configure(state='disabled')

        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)
        win.rowconfigure(4, weight=0)

        # Préparer la liste initiale triée
        items = []
        for key, info in dic_diff.items():
            sev = int(info.get('sev', 2))
            a = info.get('a')
            b = info.get('b')
            items.append((key, sev, a, b))
        items.sort(key=lambda x: (-x[1], x[0]))

        # Helpers
        def short(v, n=140):
            s = str(v) if v is not None else ''
            return s if len(s) <= n else (s[:n-1] + '…')
        #TODO : à ajuster
        def aggregate_by_parent(self,items_list):
            #from collections import defaultdict
            children = defaultdict(list)
            for key, sev, a, b in items_list:
                parts = key.rsplit('>', 1)
                parent = parts[0] if len(parts) == 2 else key
                children[parent].append((key, sev, a, b))

            groups = []
            for parent in list(children.keys()):
                child_list = children[parent]
                max_sev = max(c[1] for c in child_list)
                def uniq_vals(idx):
                    seen = []
                    for c in child_list:
                        s = str(c[idx]) if c[idx] is not None else ''
                        if s not in seen:
                            seen.append(s)
                    return seen
                agg_a = ' | '.join(uniq_vals(2))
                agg_b = ' | '.join(uniq_vals(3))
                groups.append((parent, max_sev, agg_a, agg_b, len(child_list)))
            return groups, children

        def update_status():
            total = len(items)
            c0 = sum(1 for it in items if it[1] == 0)
            c1 = sum(1 for it in items if it[1] == 1)
            c2 = sum(1 for it in items if it[1] == 2)
            visible = len(tree.get_children())
            status.config(text=f"Total {total}  |  visible {visible}  |  sev0={c0}  sev1={c1}  sev2={c2}  |  comparisons={getattr(otf,'nbr_cmp', 'N/A')}")

        # expand/collapse helpers
        def expand_all():
            for pid in tree.get_children(''):
                tree.item(pid, open=True)

        def collapse_all():
            for pid in tree.get_children(''):
                tree.item(pid, open=False)

        @staticmethod
        def toggle_selected():
            sel = tree.selection()
            if not sel: return
            for iid in sel:
                tree.item(iid, open=(not tree.item(iid, 'open')))

        # Context menu for tree (right-click)
        menu = tk.Menu(win, tearoff=0)
        menu.add_command(label="Développer", command=lambda: [tree.item(iid, open=True) for iid in tree.selection()])
        menu.add_command(label="Réduire", command=lambda: [tree.item(iid, open=False) for iid in tree.selection()])
        menu.add_separator()
        menu.add_command(label="Copier", command=lambda: copy_selection())
        menu.add_command(label="Voir détail", command=lambda: [open_detail_window(tree.item(iid)['text'], dic_diff.get(tree.item(iid)['text'], {})) for iid in tree.selection()])

        def on_right_click(event):
            iid = tree.identify_row(event.y)
            if iid:
                tree.selection_set(iid)
                menu.tk_popup(event.x_root, event.y_root)

        tree.bind("<Button-3>", on_right_click)

        # Refresh / insertion hiérarchique
        def refresh_view():
            tree.delete(*tree.get_children())
            txt = entry_search.get().strip().lower()

            sel = combo_sev.get()
            if sel == "Toutes":
                show0 = show1 = show2 = True
            else:
                try:
                    s = int(sel.split(' ')[0])
                    show0 = (s == 0)
                    show1 = (s == 1)
                    show2 = (s == 2)
                except Exception:
                    show0 = show1 = show2 = True

            show_a = var_show_a.get()
            show_b = var_show_b.get()

            filtered = []
            for key, sev, a, b in items:
                if sev == 0 and not show0: continue
                if sev == 1 and not show1: continue
                if sev == 2 and not show2: continue
                hay = f"{key} {a if a is not None else ''} {b if b is not None else ''}".lower()
                if txt and txt not in hay: continue
                filtered.append((key, sev, a, b))

            groups, children_map = aggregate_by_parent(self, filtered)
            for parent_key, group_sev, agg_a, agg_b, child_count in groups:
                tag = f"sev{group_sev}"
                display_a = short(agg_a) if show_a else ''
                display_b = short(agg_b) if show_b else ''
                parent_label = parent_key if child_count == 1 and parent_key == children_map[parent_key][0][0] else f"{parent_key} ({child_count})"
                parent_iid = tree.insert('', 'end', text=parent_label, values=(str(group_sev), display_a, display_b), tags=(tag,))
                for child in children_map[parent_key]:
                    key, sev, a, b = child
                    child_tag = f"sev{sev}"
                    child_display_key = key.rsplit('>', 1)[-1]  # ne montrer que le dernier segment pour la lisibilité
                    tree.insert(parent_iid, 'end', text=child_display_key, values=(str(sev), short(a) if show_a else '', short(b) if show_b else ''), tags=(child_tag,))
                # parent fermé par défaut
                tree.item(parent_iid, open=False)

            update_status()

        # Selection et detail
        def on_select(event):
            sel = tree.selection()
            if not sel: return
            iid = sel[0]
            # récupérer texte (chemin affiché) et valeurs
            chemin_display = tree.item(iid)['text']
            vals = tree.item(iid)['values']
            # s'il y a des enfants => parent : afficher détail agrégé
            if tree.get_children(iid):
                content_lines = []
                for cid in tree.get_children(iid):
                    child_text = tree.item(cid)['text']
                    child_vals = tree.item(cid)['values']
                    # reconstruire la clé complète si nécessaire: children_map stores full keys in items, but we don't store mapping here.
                    content_lines.append(f"{child_text} | sev={child_vals[0]}\nA: {child_vals[1]}\nB: {child_vals[2]}\n")
                detail = f"Groupe: {chemin_display}\n\n" + "\n".join(content_lines)
            else:
                # enfant : chemin_display est le dernier segment ; il faut retrouver la clé complète dans dic_diff
                # recherhce par suffixe (meilleure heuristique si noms uniques)
                key_full = None
                for k in dic_diff.keys():
                    if k.endswith('>' + chemin_display) or k == chemin_display:
                        key_full = k
                        break
                info = dic_diff.get(key_full, {})
                detail = f"Niveau: {key_full or chemin_display}\nSévérité: {info.get('sev')}\n\nValeur A:\n{info.get('a')}\n\nValeur B:\n{info.get('b')}\n"
            detail_text.configure(state='normal')
            detail_text.delete('1.0', tk.END)
            detail_text.insert(tk.END, detail)
            detail_text.configure(state='disabled')

        tree.bind("<<TreeviewSelect>>", on_select)

        def open_detail_window(chemin, info):
            w = tk.Toplevel(win)
            w.title("Détail: " + (chemin[:80] + '…' if len(chemin)>80 else chemin))
            txt = scrolledtext.ScrolledText(w, width=120, height=30, wrap='word')
            txt.pack(fill='both', expand=True, padx=6, pady=6)
            content = f"Niveau: {chemin}\nSévérité: {info.get('sev')}\n\nValeur A:\n{info.get('a')}\n\nValeur B:\n{info.get('b')}\n"
            txt.insert('1.0', content)
            txt.configure(state='disabled')
            ttk.Button(w, text="Copier", command=lambda: (w.clipboard_clear(), w.clipboard_append(content), messagebox.showinfo("Copier", "Copié"))).pack(pady=(0,6))

        def on_double_click(event):
            sel = tree.selection()
            if not sel: return
            iid = sel[0]
            if tree.get_children(iid):
                chemin_display = tree.item(iid)['text']

                content_lines = []
                for cid in tree.get_children(iid):
                    cvals = tree.item(cid)['values']
                    content_lines.append(f"{tree.item(cid)['text']} | sev={cvals[0]}\nA: {cvals[1]}\nB: {cvals[2]}\n")
                content = f"Groupe: {chemin_display}\n\n" + "\n".join(content_lines)
                open_detail_window(chemin_display, {'sev':'', 'a':'', 'b':content})
            else:
                child_display = tree.item(iid)['text']
                key_full = None
                for k in dic_diff.keys():
                    if k.endswith('>' + child_display) or k == child_display:
                        key_full = k
                        break
                info = dic_diff.get(key_full, {})
                open_detail_window(key_full or child_display, info)

        tree.bind("<Double-1>", on_double_click)

        # Exporter ou/et copier les résultats 
        def export_diff(csv_mode=True):
            ftypes = [('CSV files','*.csv')] if csv_mode else [('Text files','*.txt')]
            def_path = '.'
            path = filedialog.asksaveasfilename(initialdir=def_path, defaultextension='.csv' if csv_mode else '.txt', filetypes=ftypes)
            if not path: return
            try:
                if csv_mode:
                    with open(path, 'w', newline='', encoding='utf-8') as fh:
                        writer = csv.writer(fh)
                        writer.writerow(['Niveau', 'sev', 'A', 'B'])
                        for key, sev, a, b in items:
                            writer.writerow([key, sev, a, b])
                else:
                    with open(path, 'w', encoding='utf-8') as fh:
                        fh.write(f"{getattr(otf,'description','')}\n\n")
                        for key, sev, a, b in items:
                            fh.write(f"{key} | sev={sev}\nA: {a}\nB: {b}\n\n")
                messagebox.showinfo("Export", f"Export terminé: {path}")
            except Exception as e:
                messagebox.showerror("Erreur export", str(e))

        def copy_selection():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Copier", "Aucune ligne sélectionnée")
                return
            lines = []
            for iid in sel:
                if tree.get_children(iid):
                    for cid in tree.get_children(iid):
                        cvals = tree.item(cid)['values']
                        lines.append(f"{tree.item(cid)['text']} | sev={cvals[0]}\nA: {cvals[1]}\nB: {cvals[2]}\n")
                else:
                    display = tree.item(iid)['text']
                    key_full = None
                    for k in dic_diff.keys():
                        if k.endswith('>' + display) or k == display:
                            key_full = k
                            break
                    info = dic_diff.get(key_full, {})
                    lines.append(f"{key_full or display} | sev={info.get('sev')}\nA: {info.get('a')}\nB: {info.get('b')}\n")
            try:
                win.clipboard_clear()
                win.clipboard_append("\n".join(lines))
                messagebox.showinfo("Copier", "Sélection copiée dans le presse-papiers")
            except Exception as e:
                messagebox.showerror("Erreur copier", str(e))

        # Bindings utiles
        entry_search.bind("<KeyRelease>", lambda ev: refresh_view())
        var_show_a.trace_add('write', lambda *args: refresh_view())
        var_show_b.trace_add('write', lambda *args: refresh_view())
        win.bind_all("<plus>", lambda e: expand_all())
        win.bind_all("<Key-+>", lambda e: expand_all())
        win.bind_all("<minus>", lambda e: collapse_all())
        win.bind_all("<Key-minus>", lambda e: collapse_all())
        win.bind_all("<space>", lambda e: toggle_selected())
        # Initialisation
        refresh_view()
        win.mainloop()

if __name__ == '__main__':
    """ Si lancement en tant que script.
    """
    gui = guiOTF()
    gui.select_input()            # idem gui_selection_etus, sauf que les résultats sont retenus dans des variables membres
    gui.afficher_differences()




