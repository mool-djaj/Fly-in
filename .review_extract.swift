import Foundation
import PDFKit

let url = URL(fileURLWithPath: "/Users/akaarich/Desktop/Fly-in/en.subject (1).pdf")
guard let document = PDFDocument(url: url) else {
    fatalError("Unable to open PDF")
}

for pageIndex in 0..<document.pageCount {
    print("=== PAGE \(pageIndex + 1) ===")
    print(document.page(at: pageIndex)?.string ?? "")
}
