import tkinter
from tkinter import filedialog
from tkinter import ttk
import os, webbrowser, json

class CreateToolTip(object):
	"""
	create a tooltip for a given widget
	"""
	def __init__(self, widget, text='widget info'):
		self.waittime = 500     #miliseconds
		self.wraplength = 500   #pixels
		self.widget = widget
		self.text = text
		self.widget.bind("<Enter>", self.enter)
		self.widget.bind("<Leave>", self.leave)
		self.widget.bind("<ButtonPress>", self.leave)
		self.id = None
		self.tw = None

	def enter(self, event=None):
		self.schedule()

	def leave(self, event=None):
		self.unschedule()
		self.hidetip()

	def schedule(self):
		self.unschedule()
		self.id = self.widget.after(self.waittime, self.showtip)

	def unschedule(self):
		id = self.id
		self.id = None
		if id:
			self.widget.after_cancel(id)

	def showtip(self, event=None):
		x = y = 0
		x, y, cx, cy = self.widget.bbox("insert")
		x += self.widget.winfo_rootx() + 25
		y += self.widget.winfo_rooty() + 20
		# creates a toplevel window
		self.tw = tkinter.Toplevel(self.widget)
		# Leaves only the label and removes the app window
		self.tw.wm_overrideredirect(True)
		self.tw.wm_geometry("+%d+%d" % (x, y))
		label = ttk.Label(self.tw, text=self.text, justify='left',
					   background="#ffffff", relief='solid', borderwidth=1,
					   wraplength = self.wraplength)
		label.pack(ipadx=1)

	def hidetip(self):
		tw = self.tw
		self.tw= None
		if tw:
			tw.destroy()

class Dialog():
	def __init__( self ):
		self.root = tkinter.Tk()
		self.root.wm_attributes( '-toolwindow', 'True' )
		self.root.title( 'Import Map' )

		self.s1gameinfopath = tkinter.StringVar()
		self.s1contentdir = tkinter.StringVar()
		self.s2gameinfodir = tkinter.StringVar()
		self.s2addon = tkinter.StringVar()
		self.mapname = tkinter.StringVar()
		self.usebsp_nomergeinstances = tkinter.IntVar()
		self.usebsp = tkinter.IntVar( value=1 )
		self.skipdeps = tkinter.IntVar()
		self.config = 'import_map_community_gui_cfg.json'

		self.LoadUserPrefs()
		self.CreateWidgets()

	def open( self ):
		self.root.mainloop()

	def __update_file( self ):
		with open( self.config, 'w' ) as outfile:
			dict = {
				's1gameinfopath': self.s1gameinfopath.get(),
				's1contentdir': self.s1contentdir.get(),
				's2gameinfodir': self.s2gameinfodir.get(),
				's2addon': self.s2addon.get(),
				'mapname': self.mapname.get(),
				'usebsp_nomergeinstances': self.usebsp_nomergeinstances.get(),
				'usebsp': self.usebsp.get(),
				'skipdeps': self.skipdeps.get()
			}
			json.dump( dict, outfile )

	def __select_file( self, strvar ):
		file = os.path.normpath( filedialog.askopenfilename( title='Open a file', initialdir='/' ) )
		strvar.set( os.path.dirname( file ) )
		self.__update_file()

	def __select_folder( self, strvar ):
		path = os.path.normpath( filedialog.askdirectory( title='Open a folder', initialdir='/' ) )
		strvar.set( path )
		self.__update_file()

	def __chk1( self ):
		if self.usebsp.get() == 1:
			self.chbx2.config( state='disabled' )
		else:
			self.chbx2.config( state='enabled' )
		self.__update_file()

	def __chk2( self ):
		if self.usebsp_nomergeinstances.get() == 1:
			self.chbx1.config( state='disabled' )
		else:
			self.chbx1.config( state='enabled' )
		self.__update_file()


	def __execute( self ):
		usebsp_str = '-usebsp' if bool( self.usebsp.get() ) else ''
		usebsp_nomergeinstances_str = '-usebsp_nomergeinstances' if bool( self.usebsp_nomergeinstances.get() ) else ''
		skipdeps_str = '-skipdeps' if bool( self.skipdeps.get() ) else ''
		cmd = 'python import_map_community.py \"{}\" \"{}\" \"{}\" \"{}\" \"{}\" {} {} {}'.format( self.s1gameinfopath.get(), self.s1contentdir.get(), self.s2gameinfodir.get(), self.s2addon.get(), self.mapname.get(), usebsp_str, usebsp_nomergeinstances_str, skipdeps_str )
		os.system( cmd )

	def __openconfluencepage():
		webbrowser.open( 'https://confluence.valve.org/pages/viewpage.action?pageId=261161026' )

	def LoadUserPrefs( self ):
		if not os.path.isfile( self.config ):
			self.__update_file()

		with open( self.config, 'r' ) as openfile:
			jo = json.load( openfile )
			try: self.s1gameinfopath.set( jo['s1gameinfopath'] )
			except LookupError: pass
			try: self.s1contentdir.set( jo['s1contentdir'] )
			except LookupError: pass
			try: self.s2gameinfodir.set( jo['s2gameinfodir'] )
			except LookupError: pass
			try: self.s2addon.set( jo['s2addon'] )
			except LookupError: pass
			try: self.mapname.set( jo['mapname'] )
			except LookupError: pass
			try: self.usebsp_nomergeinstances.set( jo['usebsp_nomergeinstances'] )
			except LookupError: pass
			try: self.usebsp.set( jo['usebsp'] )
			except LookupError: pass
			try: self.skipdeps.set( jo['skipdeps'] )
			except LookupError: pass

	def usersetpath( self, str_var ):
		normpath = os.path.normpath( str_var.get() )
		str_var.set( normpath )

	def CreateWidgets( self ):
		frm = ttk.Frame( self.root, padding=10 )
		frm.grid()

		frm_r1 = ttk.Frame( frm )
		frm_r1.grid( row=0,  column=0 )
		lbl_a = ttk.Label( frm_r1, text="s1 gameinfo dir" )
		lbl_a.pack( side='left' )
		ent_a = ttk.Entry( frm_r1, textvariable=self.s1gameinfopath )
		#ent_a.config( state='disabled' )
		ent_a.pack( side='left' )
		ent_a.bind('<Return>', lambda event, str_var=self.s1gameinfopath: self.usersetpath( str_var ) )
		btn_a = ttk.Button( frm_r1, text="...", width=3, padding=0, command=lambda:self.__select_file( self.s1gameinfopath ) )
		btn_a.pack( side='left' )
		ttp_a_str = """Path to folder containing CSGO\'s gameinfo.txt, this MUST be the 
path that contains the compiled CSGO model and material content you
want to import (e.g. .mdl, .vmt)."""
		CreateToolTip( frm_r1, ttp_a_str )

		frm_r2 = ttk.Frame( frm )
		frm_r2.grid( row=1,  column=0 )
		lbl_b = ttk.Label( frm_r2, text="s1 content dir" )
		lbl_b.pack( side='left' )
		ent_b = ttk.Entry( frm_r2, textvariable=self.s1contentdir )
		#ent_b.config( state='disabled' )
		ent_b.pack( side='left' )
		ent_b.bind('<Return>', lambda event, str_var=self.s1contentdir: self.usersetpath( str_var ) )
		btn_b = ttk.Button( frm_r2, text="...", width=3, padding=0, command=lambda:self.__select_folder( self.s1contentdir ) )
		btn_b.pack( side='left' )
		ttp_b_str = """Path to CSGO uncompiled source content, (eg. .psd .tga .smd .dmx .fbx .qc etc.).
Commonly in Source 1 these were located in the /modelsrc/ and /materialsrc/ folders
via /sdk_content/.
For the import tool, these can be anywhere, as long as your folder structure is set
up as it would be to compile S1 content so that the importer can find and use
these source files."""
		CreateToolTip( frm_r2, ttp_b_str )

		frm_r3 = ttk.Frame( frm )
		frm_r3.grid( row=2,  column=0 )
		lbl_c = ttk.Label( frm_r3, text="s2 gameinfo dir" )
		lbl_c.pack( side='left' )
		ent_c = ttk.Entry( frm_r3, textvariable=self.s2gameinfodir )
		#ent_c.config( state='disabled' )
		ent_c.pack( side='left' )
		ent_b.bind('<Return>', lambda event, str_var=self.s2gameinfodir: self.usersetpath( str_var ) )
		btn_c = ttk.Button( frm_r3, text="...", width=3, padding=0, command=lambda:self.__select_file( self.s2gameinfodir ) )
		btn_c.pack( side='left' )
		ttp_c_str = """Path to folder containing CS2's gameinfo.gi"""
		CreateToolTip( frm_r3, ttp_c_str )

		frm_r4 = ttk.Frame( frm )
		frm_r4.grid( row=3,  column=0 )
		lbl_d = ttk.Label( frm_r4, text="s2 addon name" )
		lbl_d.pack( side='left' )
		ent_d = ttk.Entry( frm_r4, textvariable=self.s2addon )
		ent_d.bind( "<Return>", ( lambda event:self.__update_file() ) )
		ent_d.pack( side='left' )
		ttp_d_str = """This is the name of CS2 Workshop addon that you wish to import
your CSGO map and assets to."""
		CreateToolTip( frm_r4, ttp_d_str )

		frm_r5 = ttk.Frame( frm )
		frm_r5.grid( row=4,  column=0 )
		lbl_e = ttk.Label( frm_r5, text="map name relative to maps\\" )
		lbl_e.pack( side='left' )
		ent_e = ttk.Entry( frm_r5, textvariable=self.mapname )
		ent_e.bind( "<Return>", ( lambda event:self.__update_file() ) )
		ent_e.pack( side='left' )
		ttp_e_str = """This is the map name (.vmf) without extension, e.g. de_examplemap.
If your map sits under a sub directory of the maps folder in
<s1contentpath> be sure to add this path before your map name.
For example: my_maps/de_examplemap"""
		CreateToolTip( frm_r5, ttp_e_str )

		frm_r6 = ttk.Frame( frm )
		frm_r6.grid( row=5,  column=0 )
		self.chbx1 = ttk.Checkbutton( frm_r6, text='Generate and use bsp on import', variable=self.usebsp, onvalue=1, offvalue=0, command=self.__chk1 )
		self.chbx1.pack( side='left' )
		ttp_f_str = """This is optional, but highly recommended.
It runs the map through a special vbsp process to generate clean map
geometry from brushes, removing hidden faces and stitching up edges,
making the CS2 version easier to work with in Hammer. It preserves
world (vis) brushes from func_detail brushes for compatibility with S2.
Note: Some drawbacks are that this parameter will also merge all func_instances
in your map and the final geometry will also be triangulated (Cleaning this
geo up is a fairly simple process though, which will be explained in another guide.)"""
		CreateToolTip( frm_r6, ttp_f_str )
		
		frm_r7 = ttk.Frame( frm )
		frm_r7.grid( row=6,  column=0 )
		self.chbx2 = ttk.Checkbutton( frm_r7, text='Generate and use bsp on import,\n but do not merge instances', variable=self.usebsp_nomergeinstances, onvalue=1, offvalue=0, command=self.__chk2 )
		self.chbx2.pack( side='left' )
		ttp_g_str = """Use this instead of -usebsp if you wish to both generate clean geo and
not merge func_instances, keeping the same hierarchy as the s1 map."""
		CreateToolTip( frm_r7, ttp_g_str )

		frm_r8 = ttk.Frame( frm )
		frm_r8.grid( row=7,  column=0 )
		self.chbx3 = ttk.Checkbutton( frm_r8, text='do not import and compile dependencies', variable=self.skipdeps, onvalue=1, offvalue=0, command=self.__update_file )
		self.chbx3.pack( side='left' )
		ttp_h_str = """Optional, skips importing all dependencies/content and only generates the vmap file(s). =
This provides a 'quick' import when iterating entities for example."""
		CreateToolTip( frm_r8, ttp_h_str )

		if self.usebsp.get() == 1:
			self.chbx2.config( state='disabled' )
		if self.usebsp_nomergeinstances.get() == 1:
			self.chbx1.config( state='disabled' )

		frm_r9 = ttk.Frame( frm )
		frm_r9.grid( row=8,  column=0 )
		ttk.Button( frm_r9, text="OK", command=self.__execute ).pack( side='left',  padx=5,  pady=5 )
		ttk.Button( frm_r9, text="Quit", command=self.root.destroy ).pack( side='left',  padx=5,  pady=5 )
		#ttk.Button( frm_r9, text="Help", command=self.__openconfluencepage ).pack( side='left',  padx=5,  pady=5 )


dlg = Dialog()
dlg.open()