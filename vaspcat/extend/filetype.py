# Python standard library modules:
import decimal as d
import math
import re
import shlex

# VaspCat modules:
from vaspcat.extend import spacegroup as sg


class Cif(object):
    '''Read cif file and output crystal geometry info for external use.
    
    Attributes:
        path: String containing the path of the cif file to be read.
        data: Dictionary populated with variables contained in the cif file.
    '''
    
    def __init__(self,path):
        
        self.path = path
        self.data = {}


    def get(self):
        '''Get atomic data from cif file by running read and parse methods.

        Returns:
            self.data: Dictionary containing the following keys -
                atom: List containing the atom names for each coordinate.
                x, y, and z: Lists containing fractional cartesian 
                    coordinates for cif file atoms.
                lat_vec: 2D list containing basis vectors for unit cell.
        '''
        
        self.read()
        self.parse()
        return self.data


    def read(self):
        '''Saves cif file keywords and their values to data dictionary.'''
        
        # Store each line from input file in a list.  Each list element
        # is divided into its individual parts by the method shlex.split.
        # Shlex is part of the standard library, and the split method 
        # separates words with spaces between them and phrases contained
        # in quotes.  For example, suppose the following line was read from
        # a cif file:
        #    
        #    _audit_creation_method   'Materials Studio'
        #
        # shlex.split would create the following list from the line:
        #
        #    ['_audit_creation_method', 'Materials Studio']
        #
        # The argument 'posix = False' ensures that ungrouped quotation marks
        # and apostrophes within a string are ignored.
        with open(self.path, 'r+') as f:
            lines_read = [shlex.split(line.strip(), posix = False)
                          for line in f
                          if line[:-2] != '' # Ignore new line characters                             
                          if not line.startswith(('#',';', 'data_'))]
        
        # Save to the dictionary atrribute 'data' that links .cif variable
        # names to the data they contain.  If the phrase loop_ is found
        # in a cif file, multiple variables can be initialized at once.
        # These multiple variables are given values on lines below the 
        # variable names, with each value separated by spaces.  The
        # following cif file code illustrates this:
        #     
        #    1  loop_
        #    2  _geom_bond_atom_site_label
        #    3  _geom_bond_distance
        #    4  O18  1.229
        #
        # In this code, the variables '_geom_bond_atom_site_label' and 
        # '_geom_bond_distance' are set equal to O18 and 1.229 
        # respectively in line 4.
        #
        # The contents of line_list are mapped to cif keywords in different
        # ways for the if statements below.  See code for details.
        keyword, line_list = [], []
    
        for line in lines_read:

            if line[0].startswith('loop'):
                keyword = line_list = []

            elif line[0].startswith('_'):                 
                if len(line) == 2:  #if keyword and value are adjacent:
                    keyword = line_list = []
                    self.data[line[0]] = line[1]
                else:  #if keyword is part of a loop:
                    keyword.append(line[0])
                    line_list = []
                    self.data[keyword[-1]] = []
                
            elif len(keyword) != len(line + line_list):
                if len(keyword) < len(line + line_list): #Too few keywords?
                    line_list.append(' '.join(line))
                    self.data[keyword[-1]].extend(line_list)
                    line_list = []
                elif len(keyword) > len(line + line_list): #Too few values?
                    line_list.append(line)

            elif len(keyword) == len(line + line_list): #Keywords == Values
                line_list.extend(line)
                for (key, value) in zip(keyword, line_list): 
                    self.data[key].append(value)
                line_list = []
   

    def parse(self):
        '''Interprets the relevant geometric data read from the cif file.'''
    
        # Remap keywords in data to new keys.  Choose between two possible
        # atom labels in the process (either '_atom_site_type_symbol'
        # or '_atom_site_label'
        keyword = ['_cell_' + label
                   for label in ('length_a','length_b','length_c',
                                 'angle_alpha', 'angle_beta', 'angle_gamma')]

        keyword += ['_atom_site_' + label
                    for label in ('fract_x','fract_y','fract_z',
                                  'type_symbol','label')]
        
        keyword += ['_symmetry_space_group_name_' + label
                    for label in ('Hall','H-M')]

        keyword += ['_space_group_name_' + label 
                    for label in ('Hall','H-M_alt')]

        new_key = ['a', 'b', 'c',
                   'alpha', 'beta', 'gamma',
                   'x', 'y', 'z',
                   'atom_name','atom_label']
        
        new_key += ['hall','h-m','hall','h-m']

        keys = zip(keyword, new_key)
        
        # Make the data dictionary only contain a subset of the total data.
        f = {k[1]:self.data[k[0]] for k in keys
             if self.data.get(k[0])}
        
        # Define keywords for math methods used in data parsing.
        decimal = lambda num: d.Decimal(num)
        radians = lambda num : decimal(math.radians(decimal(num)))
        cos = lambda num : decimal(math.cos(num))
        sin = lambda num : decimal(math.sin(num))
        
        # Define a tolerance value for finding duplicate coordinates.
        tol = decimal(0.00025)

        # Convert all numbers to decimals, with re.sub removing bracketed digits.
        # Since the largest possible element name is two letters, re.sub is 
        # used to remove extraneous numbers and capital letters from the second
        # character of the 'atom' variable.
        for key in list(f):
            
            if ((key == 'atom_name') or (key == 'atom_label' and not 
                f.get('atom'))):
                f['atom'] = [f[0] + re.sub('[^a-z]','',f[1:2].lower()) 
                                  for f in f[key]]

            elif key in ['alpha', 'beta', 'gamma']:
                f[key] = radians(re.sub(' ?\(\w+\)','',f[key]))

            elif key in ['a', 'b', 'c']:
                f[key] = decimal(re.sub(' ?\(\w+\)','',f[key])) 

            elif key in ['x', 'y', 'z']:
                f[key] = [decimal(re.sub(' ?\(\w+\)','',item)) 
                          for item in f[key]]
                
                # Bring fractional coordinates between 0 and 1.  If the 
                # coordinates are close to 0 or 1, round them off.
                for i in range(len(f[key])):
                    
                    while (f[key][i] < 0) or (f[key][i] > 1): 
                        if f[key][i] < 0:
                            f[key][i] += 1
                        elif f[key][i] > 1:
                            f[key][i] -= 1

                    if abs(f[key][i]-0) < tol/10:
                        f[key][i] = decimal(0)
                    elif abs(f[key][i]-1) < tol/10:
                        f[key][i] = decimal(1)
                
            elif key in ['h-m']:
                f[key] = re.sub(r'\s+','',f[key])  # Remove spaces in H-M name.
                f[key] = f[key].replace("'",'').lower()
            
            elif key in ['hall']:
                f[key] = f[key].replace("'",'').lower()
        
        # Calculate the lattice vectors, outputting as 2D array in self.data.
        # v is the unit cell volume.
        v = (f['a']*f['b']*f['c']*
             (1 - cos(f['alpha'])**2 - cos(f['beta'])**2 - cos(f['gamma'])**2 +
              2*cos(f['alpha'])*cos(f['beta'])*cos(f['gamma']))**decimal(0.5))
        
        self.data = {'lat_vec': [
                   # a vector
                   [f['a'], 0, 0],
                   
                   # b vector
                   [f['b']*cos(f['gamma']), f['b']*sin(f['gamma']),0],
                   
                   # c vector
                   [f['c']*cos(f['beta']),
                    f['c']*(cos(f['alpha'])- cos(f['beta'])*cos(f['gamma']))/
                    sin(f['gamma']), 
                    v/(f['a']*f['b']*sin(f['gamma']))]
                  ]}
        
        # Determine the general position equations associated with
        # the space group of the crystal.  The equations are obtained
        # from the dictionaries of the module spacgroup.py (sg).
        hall_dict = {key.lower():key for key in sg.HM2Hall}
        sym_dict = {key.lower():key for key in sg.SymOpsHall}

        if f.get('hall'):
            eq = [''.join(eq) for eq in sg.SymOpsHall[sym_dict[f['hall']]]
                  if ''.join(eq) != 'x y z']
        
        elif f.get('h-m'):
            hall = sg.HM2Hall[hall_dict[f['h-m']]].lower()
            eq = [''.join(eq) for eq in sg.SymOpsHall[sym_dict[hall]]
                  if ''.join(eq) != 'x y z']

        else:
            eq = []
        
        # Put a zero in front of any negative sign in the equations read.
        # This is to avoid an exception when the expressions are evaluated
        # by the calc method later on.
        for i,expr in enumerate(eq):
            for j,char in enumerate(expr):
                
                diff = len(expr) - len(eq[i]) 

                if char == '-':
                    if j == 0:
                        expr = '0' + expr
                    elif eq[i][j-1] not in ('x','y','z'):
                        expr = expr[:j+diff] + '0' + eq[i][j:]
            
            eq[i] = expr
        
        # Apply the expressions to every coordinate read from the cif file.
        # Store the read coordinates in the new_f dictionary while looping.
        if eq:
            
            for i in range(len(f['atom'])):
                
                new_f = {}
                for var in ('x','y','z'):
                    new_f[var] = f[var][i]
                    
                # Evaluate each coordinate in new_eq by splitting each 
                # expression list into individual coordinates 
                # and calling the calc method.
                for expr in eq:
                    f['atom'].append(f['atom'][i])
                    
                    new_eq = {} 
                    new_eq['x'],new_eq['y'],new_eq['z'] = expr.split()
                                                
                    for var in ('x','y','z'):
                        new_eq[var] = new_eq[var].strip()
                        new_coor = self.calc(new_eq[var],new_f)
                        
                        while (new_coor < 0) or (new_coor > 1):
                            if new_coor > 1:
                                new_coor -= 1 
                            elif new_coor < 0:
                                new_coor += 1
                        
                        if abs(new_coor-0) < tol/10:
                            new_coor = decimal(0)
                        elif abs(new_coor-1) < tol/10:
                            new_coor = decimal(1)

                        f[var].append(new_coor)

        # Bring atoms with coordinates of 0 or 1 to the opposite side 
        # of the unit cell using 3 different criteria.
        for i in range(len(f['atom'])): 
            new_coor = {}

            for var1 in ('x','y','z'):
                
                if f[var1][i] == 0  or f[var1][i] == 1:
                    for case in range(1,4): 
                        for var2 in ('x','y','z'):
                            
                            # Case 1: Flip var2 between 0 and 1.
                            if case == 1:
                                if var2 == var1:
                                    
                                    if f[var2][i] == 0: 
                                        new_coor[var2] = decimal(1)   
                                    elif f[var2][i] == 1:
                                        new_coor[var2] = decimal(0)
                                
                                else:
                                    new_coor[var2] = f[var2][i]
                            
                            # Case 2: Flip all but var2 between 0 and 1.
                            elif case == 2:
                                if var2 != var1:
                                    
                                    if f[var2][i] == 0:
                                        new_coor[var2] = decimal(1)    
                                    elif f[var2][i] == 1:
                                        new_coor[var2] = decimal(0)
                                
                                else:
                                    new_coor[var2] = f[var2][i]
                            
                            # Case 3: Flip everything between 0 and 1.
                            elif case == 3:
                                
                                if f[var2][i] == 0:
                                    new_coor[var2] = decimal(1)
                                elif f[var2][i] == 1:
                                    new_coor[var2] = decimal(0)  
                                else:
                                    new_coor[var2] == f[var2][i]
                            
                            f[var2].append(new_coor[var2])
                        f['atom'].append(f['atom'][i])
        
        # Grab the keys 'x', 'y', 'z', and 'atom' in the proper order
        # from key_list.  Remove duplicate coordinates, and save the 
        # result to the data instance variable.          
        key_list = [key for key in f 
                    if key in ('x','y','z','atom')]
        output = [[f[key][i] for key in key_list]
                  for i in range(len(f['atom']))]
        
        # If less than 1000 atoms are in a unit cell, test if coordinates
        # are duplicates due to slight precision errors.  The number
        # 1000 was decided upon through program testing, as comparing
        # too many atoms slowed the program down without finding duplicates.
        if len(output) <= 1000:
            
            for i in range(len(output[0])):
                if type(output[0][i]) is str:
                    str_loc = i
                    break
            
            for i in range(len(output)):
                for j in range(i+1,len(output)):
                
                    if output[i][str_loc] == output[j][str_loc]:
                        for k in range(4):
                        
                            if k != str_loc:
                                if output[i][k] == output[j][k]:
                                    continue
                                elif abs(output[i][k]-output[j][k]) < tol:
                                    continue
                                else:
                                    break

                        else:
                            for k in range(4): 
                                output[j][k] = output[i][k]
                            break 
        
        # Remove duplicate atoms that have identical coordinates.
        output = [list(value) 
                  for value in set(tuple(lst) for lst in output)]
        self.data.update({key:[value[i] for value in output]
                          for i,key in enumerate(key_list)})


    def calc(self,expr,new_f):
        '''Returns fractional coordinate from space group expression.
        
        Args:
            expr: String coordinate expression to be calculated.
            new_f: Dictionary containing fractional coordinates to 
                be substituted for x/y/z in expr.
        
        Returns:
            Decimal fractional coordinate that results from evaluating expr.
        '''
        
        # Define method for easy conversion of strings to decimals.
        decimal = lambda num: d.Decimal(num)
        
        # If the expression contains a fraction, calculate it.  
        # Replace the fraction with the character f, to be used later.
        for i,char in enumerate(expr):
            if char == '/':
                left = decimal(expr[i-1])
                right = decimal(expr[i+1])
                fract = left/right

                expr = expr[:i-1] + 'f' + expr[i+2:]
                break

        i,ans = 0,decimal(0)
        
        # Reduce the expression to a single character by performing additon
        # and substraction operations.  Replace the parts of the expression
        # that have already been evaluated with a, representing the answer.
        while expr not in ('x','y','z','a','f'):
            if expr[i] in ('+','-'):
                lchar = expr[i-1]
                rchar = expr[i+1]

                if lchar in ('x','y','z'):
                    left = new_f[lchar]
                elif lchar == 'f':
                    left = fract
                elif lchar == 'a':
                    left = ans
                else:
                    left = decimal(lchar)

                if rchar in ('x','y','z'):
                    right = new_f[rchar]
                elif rchar == 'f':
                    right = fract
                elif rchar == 'a':
                    right = ans
                else:
                    right = decimal(rchar)

                if expr[i] == '+':
                    ans = left + right
                elif expr[i] == '-':
                    ans = left - right

                expr = 'a' + expr[i+2:]
                i = 0

            else:
                i += 1
        
        # Depending on what character remains, return the result.
        if expr == 'a':
            return ans
        elif expr == 'f':
            return fract
        elif expr in ('x','y','z'):
            return new_f[expr]


class Pdb(object):
    ''''Read pdb file and output crystal geometry info for external use.
    
    Attributes:
        path: String containing the path of the pdb file to be read. 
        data: Dictionary populated with variables contained in the pdb file.
    '''
    
    def __init__(self,path):
        
        self.path = path
        self.data = {}

    
    def get(self):
        '''Get atomic data from pdb file by running read and parse methods.

        Returns:
            self.data: Dictionary containing the following keys -
                atom: List containing the atom name for each coordinate. 
                x, y, and z: Lists containing fractional cartesian coordinates
                    for pdb file atoms.
                lat_vec - 2D list containg basis vectors for unit cell.
        '''

        self.read()
        self.parse()
        return self.data


    def read(self):
        '''Saves pdb file keywords and their values to data dictionary.'''

        keyword = ('CRYST1', 'SCALE', 'ATOM', 'HETATM')

        with open(self.path, 'r+') as f:
            lines_read = [line for line in f if line.startswith(keyword)]

        self.data = {'x':[], 'y':[], 'z':[], 'atom':[]}

        # Define methods needed for reading pdb files.
        decimal = lambda num: d.Decimal(num)
        radians = lambda num : decimal(math.radians(decimal(num)))

        # Set value of keys in output based on field positions in a given
        # line.  Next to each record name are fields representing different 
        # variable values.  The fields are always located in the same 
        # position next to a record name.  The if statements take advantage
        # of this consistency, reading fields from the same position 
        # if a record name is recognized.
        for line in lines_read:

            if line.startswith('CRYST1'):
                self.data['a'] = decimal(line[6:15].strip())
                self.data['b'] = decimal(line[15:24].strip())
                self.data['c'] = decimal(line[24:33].strip())
                
                self.data['alpha'] = radians(line[33:40].strip())
                self.data['beta'] = radians(line[40:47].strip())
                self.data['gamma'] = radians(line[47:54].strip())

                self.data['h-m'] = line[55:66].replace(' ','').lower().rstrip()

            elif line.startswith('SCALE'):
                self.data['s' + line[5]] = [decimal(line[10:20].strip()),
                                            decimal(line[20:30].strip()),
                                            decimal(line[30:40].strip())]
        
                self.data['u' + line[5]] = decimal(line[45:55].strip())
            
            elif line.startswith(('ATOM', 'HETATM')):
                if line[12].upper() == 'H':
                    self.data['atom'].append(line[12])
                elif line[12] == ' ':
                    self.data['atom'].append(line[13])
                else:
                    self.data['atom'].append(line[12] + line[13].lower())
            
                self.data['x'].append(decimal(line[30:38].strip()))
                self.data['y'].append(decimal(line[38:46].strip()))
                self.data['z'].append(decimal(line[46:54].strip()))
   

    def parse(self):
        ''''Interprets the relevant geometric data read from the pdb file.'''
        
        # Use the dictionary f to simplify calls to self.data.
        f = self.data
        
        # Define keywords for math methods used in data parsing.
        decimal = lambda num: d.Decimal(num)
        cos = lambda num : decimal(math.cos(num))
        sin = lambda num : decimal(math.sin(num))

        # Define a tolerance value for finding duplicate coordinates.
        tol = decimal('0.00025')
        
        # Calculate the lattice vectors, outputting as 2D list.
        # v is the unit cell volume.
        v = (f['a']*f['b']*f['c']*
            (1 - cos(f['alpha'])**2 - cos(f['beta'])**2 - cos(f['gamma'])**2 +
                2*cos(f['alpha'])*cos(f['beta'])*cos(f['gamma'])).sqrt())
       
        self.data = {'lat_vec': [
                   # a vector
                   [f['a'], 0, 0],
                   
                   # b vector
                   [f['b']*cos(f['gamma']), f['b']*sin(f['gamma']),0],
                   
                   # c vector
                   [f['c']*cos(f['beta']),
                    f['c']*(cos(f['alpha'])- cos(f['beta'])*cos(f['gamma']))/
                    sin(f['gamma']), 
                    v/(f['a']*f['b']*sin(f['gamma']))]
                  ]}
 
        # Convert the supplied orthogonal coordinates to fractional coordinates.
        xyz = list(zip(f['x'], f['y'], f['z']))
        ortho = [vec for vec in xyz]

        key_tup = (('x','1'),('y','2'), ('z','3'))

        for key,i in key_tup:
            s = 's' + i
            u = 'u' + i
            f[key] = [f[s][0]*vec[0] + f[s][1]*vec[1] + f[s][2]*vec[2] + f[u]
                      for vec in ortho]
        
        # Bring new coordinates between 0 and 1.  If the coordinates are very
        # close to 0 or 1, round them off.
        for key in ('x','y','z'):
            for i in range(len(f['atom'])):
                while (f[key][i] > 1) or (f[key][i] < 0):

                    if f[key][i] > 1:
                        f[key][i] -= 1
                    elif f[key][i] < 0:
                        f[key][i] += 1
                
                if abs(f[key][i]-0) < tol/10:
                    f[key][i] = decimal(0)
                elif abs(f[key][i]-1) < tol/10:
                    f[key][i] = decimal(1)

        # Determine the general position equations associated with
        # the space group of the crystal.  The equations are obtained
        # from the dictionaries of the module spacgroup.py (sg).
        hall_dict = {key.lower():key for key in sg.HM2Hall}
        sym_dict = {key.lower():key for key in sg.SymOpsHall}

        if f.get('h-m'):
            hall = sg.HM2Hall[hall_dict[f['h-m']]].lower()
            eq = [''.join(eq) for eq in sg.SymOpsHall[sym_dict[hall]]
                  if ''.join(eq) != 'x y z']
        else:
            eq = []
        
        # Put a zero in front of any negative sign in the equations read.
        # This is to make evaluation easier when the expressions are evaluated
        # by the calc method later on.
        for i,expr in enumerate(eq):
            for j,char in enumerate(expr):
                
                diff = len(expr) - len(eq[i]) 

                if char == '-':
                    if j == 0:
                        expr = '0' + expr
                    elif eq[i][j-1] not in ('x','y','z'):
                        expr = expr[:j+diff] + '0' + eq[i][j:]

            eq[i] = expr
        
        # Apply the expressions to every coordinate read from the pdb file.
        # Store the read coordinates in the new_f dictionary while looping.
        if eq:
            
            for i in range(len(f['atom'])):
                
                new_f = {}
                for var in ('x','y','z'):
                    new_f[var] = f[var][i]
                    
                # Evaluate each coordinate in new_eq by splitting each 
                # expression list into individual coordinates 
                # and calling the calc method.
                for expr in eq:
                    f['atom'].append(f['atom'][i])
                    
                    new_eq = {} 
                    new_eq['x'],new_eq['y'],new_eq['z'] = expr.split()
                                                
                    for var in ('x','y','z'):
                        new_eq[var] = new_eq[var].strip()
                        new_coor = self.calc(new_eq[var],new_f)
                        
                        while (new_coor < 0) or (new_coor > 1):
                            if new_coor > 1:
                                new_coor -= 1 
                            elif new_coor < 0:
                                new_coor += 1
                        
                        if abs(new_coor-0) < tol/10:
                            new_coor = decimal(0)
                        elif abs(new_coor-1) < tol/10:
                            new_coor = decimal(1)

                        f[var].append(new_coor)
        
        # Bring atoms with coordinates of 0 or 1 to the opposite side 
        # of the unit cell using 3 different criteria.
        for i in range(len(f['atom'])): 
            new_coor = {}

            for var1 in ('x','y','z'):
                
                if f[var1][i] == 0 or f[var1][i] == 1:
                    for case in range(1,4): 
                        for var2 in ('x','y','z'):
                            
                            # Case 1: Flip var2 between 0 and 1.
                            if case == 1:
                                if var2 == var1:
                                    
                                    if f[var2][i] == 0: 
                                        new_coor[var2] = decimal(1)   
                                    elif f[var2][i] == 1:
                                        new_coor[var2] = decimal(0)
                                
                                else:
                                    new_coor[var2] = f[var2][i]
                            
                            # Case 2: Flip all but var2 between 0 and 1.
                            elif case == 2:
                                if var2 != var1:
                                    
                                    if f[var2][i] == 0:
                                        new_coor[var2] = decimal(1)    
                                    elif f[var2][i] == 1:
                                        new_coor[var2] = decimal(0)
                                
                                else:
                                    new_coor[var2] = f[var2][i]
                            
                            # Case 3: Flip everything between 0 and 1.
                            elif case == 3:
                                
                                if f[var2][i] == 0:
                                    new_coor[var2] = decimal(1)
                                elif f[var2][i] == 1:
                                    new_coor[var2] = decimal(0)
                                else:
                                    new_coor[var2] == f[var2][i]
                            
                            f[var2].append(new_coor[var2])
                        f['atom'].append(f['atom'][i])
        
        # Grab the keys 'x', 'y', 'z', and 'atom' in the proper order
        # from key_list.  Remove duplicate coordinates, and save the 
        # result to the data instance variable.          
        key_list = [key for key in f 
                    if key in ('x','y','z','atom')]
        output = [[f[key][i] for key in key_list]
                  for i in range(len(f['atom']))]
        
        # If less than 1000 atoms are in a unit cell, test if coordinates
        # are duplicates due to slight precision errors.  The number
        # 1000 was decided upon through program testing, as comparing
        # too many atoms slowed the program down without finding duplicates.
        if len(output) <= 1000:
            
            for i in range(len(output[0])):
                if type(output[0][i]) is str:
                    str_loc = i
                    break
            
            for i in range(len(output)):
                for j in range(i+1,len(output)):
                
                    if output[i][str_loc] == output[j][str_loc]:
                        for k in range(4):
                        
                            if k != str_loc:
                                if output[i][k] == output[j][k]:
                                    continue
                                elif abs(output[i][k]-output[j][k]) < tol:
                                    continue
                                else:
                                    break

                        else:
                            for k in range(4): 
                                output[j][k] = output[i][k]
                            break 
        
        # Remove duplicate atoms that have identical coordinates.
        output = [list(value) 
                  for value in set(tuple(lst) for lst in output)]
        self.data.update({key:[value[i] for value in output]
                          for i,key in enumerate(key_list)})
        
    
    def calc(self,expr,new_f):
        '''Returns fractional coordinate from space group expression.
        
        Args:
            expr: String coordinate expression to be calculated.
            new_f: Dictionary containing fractional coordinates to 
                be substituted for x/y/z in expr.
        
        Returns:
            Decimal fractional coordinate that results from evaluating expr.
        '''
        
        # Define method for easy conversion of strings to decimals.
        decimal = lambda num: d.Decimal(num)
        
        # If the expression contains a fraction, calculate it.  
        # Replace the fraction with the character f, to be used later.
        for i,char in enumerate(expr):
            if char == '/':
                left = decimal(expr[i-1])
                right = decimal(expr[i+1])
                fract = left/right

                expr = expr[:i-1] + 'f' + expr[i+2:]
                break

        i,ans = 0,decimal(0)
        
        # Reduce the expression to a single character by performing additon
        # and substraction operations.  Replace the parts of the expression
        # that have already been evaluated with a, representing the answer.
        while expr not in ('x','y','z','a','f'):
            if expr[i] in ('+','-'):
                lchar = expr[i-1]
                rchar = expr[i+1]

                if lchar in ('x','y','z'):
                    left = new_f[lchar]
                elif lchar == 'f':
                    left = fract
                elif lchar == 'a':
                    left = ans
                else:
                    left = decimal(lchar)

                if rchar in ('x','y','z'):
                    right = new_f[rchar]
                elif rchar == 'f':
                    right = fract
                elif rchar == 'a':
                    right = ans
                else:
                    right = decimal(rchar)

                if expr[i] == '+':
                    ans = left + right
                elif expr[i] == '-':
                    ans = left - right

                expr = 'a' + expr[i+2:]
                i = 0

            else:
                i += 1
        
        # Depending on what character remains, return the result.
        if expr == 'a':
            return ans
        elif expr == 'f':
            return fract
        elif expr in ('x','y','z'):
            return new_f[expr]
