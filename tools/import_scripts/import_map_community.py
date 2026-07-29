##########################################################################################################################################
#
# import_map script
#  
##########################################################################################################################################

from __future__ import print_function
import os
import argparse
import time
import ast

from utils import utlc as utl

##########################################################################################################################################
#
##########################################################################################################################################
def StripMDLsFromRefs( filename ):

	refs = utl.ReadTextFile( filename )

	mdls = []
	others = []
	utl.SplitMdlFromRefs( mdls, others, refs )

	mdlfilename = filename.replace( "_refs.txt", "_mdl_lst.txt" )
	utl.EnsureFileWritable( mdlfilename )
	writeFile = open( mdlfilename, "w" )
	[ writeFile.write( x + "\n" ) for x in mdls ]
	writeFile.close()

	refsfilename = filename.replace( "_refs.txt", "_new_refs.txt" )
	utl.EnsureFileWritable( refsfilename )
	writeFile = open( refsfilename, "w" )
	writeFile.write( utl.RefsStringFromList( others ) )
	writeFile.close()


##########################################################################################################################################
# Function to check meshinfo.txt and force 2UVs as required
##########################################################################################################################################

# Ensure the vmat has the F_FORCE_UV2 feature added
def ForceUV2ForVMAT( mtlfile ):

	vmatfilename = s2contentcsgoimported + "\\" + mtlfile.replace( ".vmt", ".vmat" )

	if ( not os.path.exists( vmatfilename ) ):
		return

	vmatlist = utl.ReadTextFileNoStrip( vmatfilename )

	utl.EnsureFileWritable( vmatfilename )

	for line in range( len( vmatlist ) ):
		txt = vmatlist[ line ].strip()
		txt = txt.lower()
		if txt.startswith( "\"shader\"" ):
			# line + 1 assumed to be safe since there's always at least one more line after "Shader" "bla.vfx"
			txtNext = vmatlist[ line + 1 ].strip()
			txtNext = txtNext.replace( "\t", "" )
			if ( not txtNext.startswith( "\"F_FORCE_UV2\"" ) ):
				vmatlist.insert( line + 1, "\t\"F_FORCE_UV2\" \"1\"\n" )
				break

	print( "Added F_FORCE_UV2 to %s" % vmatfilename )
	writeFile = open( vmatfilename, "w" )
	writeFile.writelines( vmatlist )
	writeFile.close()


def Force2UVsIfRequired( refsName, global2UVMaterials, global2UVMaterialsFile ):

	uvsUpdated = set()

	meshinfofilename = refsName.replace( "_refs.txt", "_refs/mesh/meshinfo.txt").replace( "/", "\\" )

	if ( not os.path.exists( meshinfofilename ) ):
		return False

	meshinfo = utl.ReadTextFile( meshinfofilename )
	meshstring = "".join( meshinfo )
	meshinfoparse = ast.literal_eval( meshstring )

	b2UV = False

	if ( not os.path.exists( refsName ) ):
		return False

	refs = utl.ReadTextFile( refsName )
	refsString = utl.ListStringFromRefs( refs )
	refsList = refsString.split( "\n" )

	for mtlfile in refsList :

		if ( not len( mtlfile ) ):
			continue

		if ( mtlfile in uvsUpdated ):
			continue

		# check if ANY materials in refslist is already a member of the global2UVMaterials, if so let's force compile the model and make sure the material still has the flag added
		if ( mtlfile in global2UVMaterials ):
			b2UV = True
			uvsUpdated.add( mtlfile )

		else:
			# add new material to forceuv2 list
			if ( meshinfoparse[ "numuvs" ] == 2 ):
				b2UV = True
				print ( "Adding F_FORCE_UV2 to mtls imported from %s..." % refsName )
			
				uvsUpdated.add( mtlfile )

				if ( mtlfile not in global2UVMaterials ):
					global2UVMaterialsFile.write( "%s\n" % mtlfile )
					global2UVMaterials.add( mtlfile )

				# Ensure the vmat has the F_FORCE_UV2 feature added
				ForceUV2ForVMAT( mtlfile )


	return b2UV

##########################################################################################################################################
#
##########################################################################################################################################
def ImportAndCompileMapMDLs( filename, s2addon, errorCallback ):

	# read list of models to convert
	mdlfiles = utl.ReadTextFile( filename )

	if ( len( mdlfiles ) < 1 ): 
		print( "No MDLs to import" )
		return 

	print( "Importing models" )
	print( "--------------------------------")
	for x in mdlfiles : 
		if ( x.startswith("-") == False):
			print(x)	
	print( "--------------------------------")

	force2UVList = []
	mdlmtls = set()

	extraoptions = ""
	for mdlfile in mdlfiles :
		if ( mdlfile.startswith( "-" ) ):
			if  ( ( mdlfile == "-" ) or ( mdlfile == "-nooptions" ) ):
				extraoptions = ""
			else:
				extraoptions = mdlfile
		else:
			mdlfile = mdlfile.replace( "/", "\\" )
			infile = mdlfile

			outName = s2contentcsgoimported + "\\" + mdlfile.replace( ".mdl", ".vmdl" )
			refsName = s2contentcsgoimported + "\\" + mdlfile.replace( ".mdl", "_refs.txt" )

			# Import

			importCmd = "cs_mdl_import -nop4 %s -i \"%s\" -o \"%s\" \"%s\"" % ( extraoptions, s1gamecsgo, s2contentcsgoimported, infile )
			utl.RunCommand( importCmd, errorCallback )

			# So we only import materials once, lets add their refs to a refsset, and import them after all models
			if ( os.path.exists( refsName ) ):
				refs = utl.ReadTextFile( refsName )
				str = utl.ListStringFromRefs( refs )
				mtllist = str.split( "\n" )
				for mtlname in mtllist : mdlmtls.add( mtlname )

				# collect refsNames so we can add 2UVs as required
				force2UVList.append( refsName )

	# import mtls used by mdl
	mdlmtlrefs = utl.RefsStringFromList( list( mdlmtls ) )

	temp_refs = filename.replace( "mdl_lst", "mtl_lst")
	utl.EnsureFileWritable( temp_refs )
	fw = open( temp_refs, "w" )
	fw.write( mdlmtlrefs )
	fw.close()

	importRefsCmd = "source1import -retail -nop4 -nop4sync -src1gameinfodir \"%s\" -s2addon %s -game csgo -usefilelist \"%s\"" % ( s1gamecsgo, s2addon, temp_refs )
	utl.RunCommand( importRefsCmd, errorCallback )

	# read in global list of materials where we've forced uv2...
	global2UVMaterials = set()
	force2UVList = utl.ReadTextFile( "source1import_2uvmateriallist.txt" )
	for mtl in force2UVList :
		global2UVMaterials.add( mtl )
		# Ensure all mtls in this list have the F_FORCE_UV2 feature added
		ForceUV2ForVMAT( mtl )

	# ...we may append to this file	
	utl.EnsureFileWritable( "source1import_2uvmateriallist.txt" )
	global2UVMaterialFile = open( "source1import_2uvmateriallist.txt", "a" )

	# compile materials
	# adding explicitly since we appear to miss a number of these if we rely on model compilation above to compile all materials refs too, even if we compile models with -f.
	for mtlfile in mdlmtls :
		if ( mtlfile.startswith( "-" ) or ( mtlfile == "" ) ):
			continue
		else:
			mtlfile = mtlfile.replace( "/", "\\" )
			outName = s2contentcsgoimported + "\\" + mtlfile.replace( ".vmt", ".vmat" )

		resCompCmd = "resourcecompiler -retail -nop4 -game csgo \"%s\"" % ( outName )
		utl.RunCommand( resCompCmd, errorCallback )

	# compile models
	for mdlfile in mdlfiles :
		bForceCompile = False
		if ( mdlfile.startswith( "-" ) ):
			continue
		else:
			mdlfile = mdlfile.replace( "/", "\\" )
			outName = s2contentcsgoimported + "\\" + mdlfile.replace( ".mdl", ".vmdl" )

			if ( not os.path.exists( outName ) ):
				continue

			refsName = s2contentcsgoimported + "\\" + mdlfile.replace( ".mdl", "_refs.txt" )
			# commenting this out for now, not needed if we're always force compiling
			bForceCompile = Force2UVsIfRequired( refsName, global2UVMaterials, global2UVMaterialFile )

		# For now just let the map importer script do the compiles
		# Compile Model ( should compile materials too ). Possibly add -f here when shader changes have happened.
		if ( bForceCompile ):
			resCompCmd = "resourcecompiler -retail -nop4 -f -game csgo \"%s\"" % ( outName )
		else:
			resCompCmd = "resourcecompiler -retail -nop4 -game csgo \"%s\"" % ( outName )

		utl.RunCommand( resCompCmd, errorCallback )

	# close global 2uv material file
	global2UVMaterialFile.close()



##########################################################################################################################################
#
##########################################################################################################################################
def ImportAndCompileMapRefs( refsFile, s2addon, errorCallback ):

	# import map refs
	importcmd = "source1import -retail -nop4 -nop4sync -src1gameinfodir \"" + s1gamecsgo + "\" -s2addon " + s2addon + " -game csgo -usefilelist \"" + refsFile + "\""
	utl.RunCommand( importcmd, errorCallback )

	refs = utl.ReadTextFile( refsFile )
	str = utl.ListStringFromRefs( refs )
	flatList = str.split( "\n" )

	newList = ""

	for line in flatList:
		if len( line ):
			line = line.replace( ".vmt", ".vmat" )
			line = line.replace( " ", "_" )
			newList += s2contentcsgoimported + "\\" + line.replace( "/", "\\" ) + "\n"

	tmpFile = s2contentcsgoimported + "\\maps\\" + mapname + "_prefab_compile_new_refs.txt"
	utl.EnsureFileWritable( tmpFile )
	writeFile = open( tmpFile, "w" )
	writeFile.write( newList )
	writeFile.close()

	compilercmd = "resourcecompiler -retail -nop4 -game csgo -f -filelist \"" + tmpFile + "\""
	utl.RunCommand( compilercmd, errorCallback )

##########################################################################################################################################
#
##########################################################################################################################################

#
# START
#

start = time.time()

# save VALVE_NO_AUTO_P4 environment var, set to 1 to ensure p4 lib works in a mode that is disconnected from p4
utl.SaveEnv()

# inputs
parser = argparse.ArgumentParser( prog='import_map_community', description='Import a map (vmf) and its dependencies from s1 to s2' )
parser.add_argument( 's1gameinfodir', help='path to s1 gameinfo.txt' )
parser.add_argument( 's1contentdir', help='path to s1 content' )
parser.add_argument( 's2gameinfodir', help='path to s2 gameinfo.gi' )
parser.add_argument( 's2addon', help='s2 addon name')
parser.add_argument( 'mapname', help='Name of map to import, relative to maps\\ in the csgo content directory' )
parser.add_argument( '-usebsp', action='store_true', default=False, help='Generate and use bsp on import' )
parser.add_argument( '-usebsp_nomergeinstances', action='store_true', default=False, help='if using bsp, do not merge instances' )
parser.add_argument( '-skipdeps', action='store_true', default=False, help='do not import and compile dependencies (imports .vmf to .vmap only)' )
args = parser.parse_args()

mapname = args.mapname
usebsp = args.usebsp
nomergeinstances = args.usebsp_nomergeinstances
skipdeps = args.skipdeps

# setup paths
s1gamecsgo = args.s1gameinfodir
s1contentcsgo = args.s1contentdir
s2gamecsgo = args.s2gameinfodir
s2addon = args.s2addon

s1gamecsgotxt = s1gamecsgo + "\\" + "gameinfo.txt"
if ( not os.path.exists( s1gamecsgotxt ) ):
	utl.Error( "%s not found, aborting" % s1gamecsgotxt )

s2gamecsgogi = s2gamecsgo + "\\" + "gameinfo.gi"
if ( not os.path.exists( s2gamecsgogi ) ):
	utl.Error( "%s not found, aborting" % s2gamecsgogi )

s2gameaddondir = "game\\csgo_addons\\" + s2addon
s2gameaddon = s2gamecsgo.replace( "game\\csgo", s2gameaddondir )

s2contentcsgo = s2gameaddon.replace( "game\csgo_addons", "content\csgo_addons" )
s2contentcsgoimported = s2contentcsgo

errorCallback = None

utl.print_color( "WARNING - this script will potentially overwrite imported content in your addon folders?\nEnter to Continue, Esc to Quit", utl.BACKGROUND_RED + utl.FOREGROUND_WHITE )
bRunImport = True
while True:
	if utl.kbd.kbhit():
		nKey = utl.kbd.getch().decode()
		if nKey == chr( 27 ): # Esc key
			bRunImport = False
			break
		if nKey == chr( 13 ): # Enter key
			bRunImport = True
			break

if ( not bRunImport ):
	utl.Error( "...aborting" )

# import vmf to vmap
mapImportCmd = "source1import -retail -nop4 -nop4sync " + "%s" %("-usebsp" if usebsp == True else "") + "%s" %(" -usebsp_nomergeinstances" if nomergeinstances == True else "") + " -src1gameinfodir \"" + s1gamecsgo + "\" -src1contentdir \"" + s1contentcsgo + "\" -s2addon \"" + s2addon + "\" -game csgo maps\\" + mapname + ".vmf"
utl.RunCommand( mapImportCmd, errorCallback )

# replace 'instance' paths with 'prefab' 
mapname = mapname.replace( "instances", "prefabs" )

if ( not skipdeps ):
	# We strip out models as they go through the new importer last
	StripMDLsFromRefs( s2contentcsgoimported + "\\maps\\" + mapname + "_prefab_refs.txt" )

	# now import mdls (as modeldoc), and their materials
	ImportAndCompileMapMDLs( s2contentcsgoimported + "\\maps\\" + mapname + "_prefab_mdl_lst.txt", s2addon, errorCallback )

	# import refs (excluding mdls)
	ImportAndCompileMapRefs( s2contentcsgoimported + "\\maps\\" + mapname + "_prefab_new_refs.txt", s2addon, errorCallback )

	# quick import vmf again (taking dependencies into account now that materials in particular have been imported/compiled) 
	utl.RunCommand( mapImportCmd, errorCallback )


# explicit copy of main .vmap to game\csgo\maps if not already there (since it can only be compiled from there)
infile = s2contentcsgo + "\\maps\\" + mapname + ".vmap"
if ( not os.path.exists( infile ) ):
	utl.RunCommand( "xcopy " + s2contentcsgoimported + "\\maps\\" + mapname + ".vmap " + s2contentcsgo + "\\maps\\" + "*" )

#
# FINISH
#

# restore VALVE_NO_AUTO_P4 environment var
utl.RestoreEnv()

#
end = time.time()

elapsedTime = end - start

utl.print_I( "import_map.py " + s1gamecsgo + " " + s1contentcsgo + " " + s2gamecsgo + " " + mapname + " " + "%s" %(" -usebsp" if usebsp == True else "") + "%s" %(" -usebsp_nomergeinstances" if nomergeinstances == True else "")+ "%s" %(" -skipdeps" if skipdeps == True else "") )
utl.print_I( "Elapsed time: " + utl.GetElapsedTime( elapsedTime ) )
