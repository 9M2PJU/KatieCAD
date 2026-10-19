        # --- Logo suchen (mehrere mögliche Orte) ---
        logo_path = None
        kandidaten = [
            "KatieCAD.png",
            os.path.join(os.getcwd(), "KatieCAD.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "KatieCAD.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "KatieCAD.png"),
        ]
        for k in kandidaten:
            k_abs = os.path.abspath(k)
            if os.path.isfile(k_abs):
                logo_path = k_abs
                break

        if logo_path is None:
            print("[KatieCAD] Logo nicht gefunden. Gesucht in:")
            for k in kandidaten:
                print(f"    {os.path.abspath(k)}")
        elif not PILLOW_VERFUEGBAR:
            print("[KatieCAD] Pillow nicht installiert – Logo wird nicht angezeigt.")
        else:
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                logo_img = logo_img.resize((64, 64), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                logo_lbl = tk.Label(title_row, image=logo_photo,
                                    bg=FARBEN["bg_mittel"], bd=0,
                                    highlightthickness=0)
                logo_lbl.image = logo_photo  # Referenz speichern!
                logo_lbl.pack(side="left", padx=(0, 14))
                print(f"[KatieCAD] Logo geladen: {logo_path}")
            except Exception as e:
                print(f"[KatieCAD] Logo konnte nicht geladen werden: {e}")
