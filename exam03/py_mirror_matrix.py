def mirror_matrix(matrix: list[list[int]]) -> list[list[int]]:
    return [i[::-1] for i in matrix]



print(mirror_matrix([[1,2,3],[4,5,6]]))
#[[3,2,1],[6,5,4]]
