def plot_centres_xsf(structure, w90_calc, filename='./wannier.xsf'):
    """
    Plots Wannier function centres in .xsf format
    """
    import sys
    import ase
    a = structure.get_ase()
    new_a = a.copy()
    out = w90_calc.out.output_parameters.get_dict()['wannier_functions_output']
    coords = [i['coordinates'] for i in out]
    for c in coords:
        new_a.append(ase.Atom('X', c))
    new_a.write(filename)
