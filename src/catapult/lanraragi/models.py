class LanraragiResponse:
    
    success: int
    status_code: int
    message: str
    error: str
    data: object
    operation: str

    def __repr__(self) -> str:
        return str(self.__dict__)
